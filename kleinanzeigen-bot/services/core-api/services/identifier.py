"""Item identification service — orchestrates LLM + pricing into a draft."""

import logging
from uuid import UUID
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Listing, ListingImage, PricingCandidate, AuditLog
from services.llm_client import identify_and_draft
from services.scraper import scrape_multiple_queries
from services.pricer import filter_and_score_candidates, compute_price
from config import settings

logger = logging.getLogger(__name__)


async def generate_draft(listing_id: UUID, db: AsyncSession) -> dict:
    """
    Full draft generation pipeline:
    1. Load listing + images
    2. LLM identification + draft
    3. Pricing via Kleinanzeigen search
    4. Save results to DB
    """
    # ── Load listing ─────────────────────────────────────
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise ValueError(f"Listing {listing_id} not found")

    if listing.status not in ("intake_received", "draft_failed"):
        logger.info(f"Listing {listing_id} already in status {listing.status}, skipping")
        return {"success": True, "listing_id": listing_id, "status": listing.status}

    # Update status
    listing.status = "draft_generating"
    await db.flush()

    # ── Load images ──────────────────────────────────────
    img_result = await db.execute(
        select(ListingImage)
        .where(ListingImage.listing_id == listing_id)
        .order_by(ListingImage.sort_order)
    )
    images = img_result.scalars().all()

    if not images:
        listing.status = "draft_failed"
        return {"success": False, "listing_id": listing_id, "error": "No images found",
                "status": "draft_failed"}

    # Use thumbnails for LLM (smaller = cheaper tokens)
    image_paths = []
    for img in images:
        path = img.thumb_path or img.file_path
        if Path(path).exists():
            image_paths.append(path)

    if not image_paths:
        listing.status = "draft_failed"
        return {"success": False, "listing_id": listing_id, "error": "No image files found on disk",
                "status": "draft_failed"}

    # ── Step 1: LLM identification ───────────────────────
    try:
        identification, model_used, raw_response = await identify_and_draft(
            image_paths=image_paths,
            user_note=listing.user_note,
        )

        listing.item_name = identification.item_name
        listing.item_category = identification.item_category
        listing.item_condition = identification.item_condition
        listing.search_terms = identification.search_terms
        listing.title = identification.title
        listing.description = identification.description
        listing.identification_confidence = identification.identification_confidence
        listing.llm_model_used = model_used
        listing.llm_raw_response = raw_response

        listing.status = "pricing_pending"
        await db.flush()

        logger.info(f"Listing {listing_id}: identified as '{identification.item_name}' "
                     f"(confidence: {identification.identification_confidence})")

    except Exception as e:
        logger.error(f"Listing {listing_id}: LLM identification failed: {e}")
        listing.status = "draft_failed"
        listing.last_posting_error = str(e)
        db.add(AuditLog(
            listing_id=listing.id,
            event_type="error",
            new_value="llm_identification_failed",
            details={"error": str(e)},
        ))
        await db.flush()
        return {"success": False, "listing_id": listing_id, "error": str(e),
                "status": "draft_failed"}

    # ── Step 2: Pricing via search ───────────────────────
    try:
        search_queries = listing.search_terms[:3] if listing.search_terms else [listing.item_name]
        search_results = await scrape_multiple_queries(search_queries, max_results_total=20)

        # Convert to dicts for pricing engine
        candidate_dicts = [
            {
                "title": r.title,
                "price": r.price,
                "price_type": r.price_type,
                "url": r.url,
                "location": r.location,
            }
            for r in search_results
        ]

        # Filter and score
        scored_candidates = filter_and_score_candidates(
            candidate_dicts,
            listing.item_name,
        )

        # Save all candidates to DB
        for c in scored_candidates:
            db.add(PricingCandidate(
                listing_id=listing.id,
                source="kleinanzeigen",
                source_url=c.get("url"),
                source_title=c.get("title"),
                source_price=c.get("price"),
                source_price_type=c.get("price_type"),
                similarity_score=round(c.get("similarity_score", 0), 2),
                is_comparable=c.get("is_comparable", False),
            ))

        # Compute price from comparable candidates
        comparable_prices = [
            c["price"] for c in scored_candidates
            if c.get("is_comparable") and c.get("price") and c["price"] > 0
        ]

        price_result = compute_price(
            prices=comparable_prices,
            strategy=settings.default_price_strategy,
            condition=listing.item_condition or "good",
        )

        listing.recommended_price = price_result.price
        listing.price_confidence = price_result.confidence
        listing.price_reasoning = price_result.reasoning
        listing.comp_count = price_result.comp_count
        listing.median_price = price_result.median
        listing.price_range_low = price_result.range_low
        listing.price_range_high = price_result.range_high
        listing.ka_location_zip = settings.default_zip

        logger.info(f"Listing {listing_id}: price={price_result.price}€ "
                     f"(confidence: {price_result.confidence}, comps: {price_result.comp_count})")

    except Exception as e:
        logger.warning(f"Listing {listing_id}: Pricing failed: {e}. "
                       "Proceeding with no-confidence pricing.")
        listing.price_confidence = "none"
        listing.price_reasoning = f"Pricing scrape failed: {e}"
        db.add(AuditLog(
            listing_id=listing.id,
            event_type="error",
            new_value="pricing_failed",
            details={"error": str(e)},
        ))

    # ── Final status ─────────────────────────────────────
    listing.status = "draft_ready"
    await db.flush()

    db.add(AuditLog(
        listing_id=listing.id,
        event_type="status_change",
        old_value="pricing_pending",
        new_value="draft_ready",
    ))

    return {
        "success": True,
        "listing_id": listing_id,
        "title": listing.title,
        "recommended_price": float(listing.recommended_price) if listing.recommended_price else None,
        "price_confidence": listing.price_confidence,
        "status": "draft_ready",
    }
