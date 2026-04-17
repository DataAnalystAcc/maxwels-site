"""Listings router — CRUD endpoints for the review UI."""

from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Listing, ListingImage, AuditLog
from schemas import (
    ListingSummaryOut, ListingDetailOut, ListingUpdateIn,
    PaginatedListings, BulkApproveIn, BulkApproveOut,
)

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=PaginatedListings)
async def list_listings(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List listings with optional status filter and pagination."""
    query = select(Listing).order_by(Listing.created_at.desc())
    count_query = select(func.count()).select_from(Listing)

    if status:
        query = query.where(Listing.status == status)
        count_query = count_query.where(Listing.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.offset(offset).limit(limit))
    listings = result.scalars().all()

    items = []
    for listing in listings:
        # Load images for thumbnail + count
        img_result = await db.execute(
            select(ListingImage)
            .where(ListingImage.listing_id == listing.id)
            .order_by(ListingImage.sort_order)
        )
        images = img_result.scalars().all()

        thumbnail_url = None
        if images:
            thumbnail_url = f"/images/{listing.id}/{images[0].file_name}"
            if images[0].thumb_path:
                thumbnail_url = images[0].thumb_path.replace("/data", "")

        items.append(ListingSummaryOut(
            id=listing.id,
            status=listing.status,
            title=listing.title,
            item_name=listing.item_name,
            item_category=listing.item_category,
            item_condition=listing.item_condition,
            recommended_price=listing.recommended_price,
            final_price=listing.final_price,
            price_confidence=listing.price_confidence,
            identification_confidence=listing.identification_confidence,
            thumbnail_url=thumbnail_url,
            image_count=len(images),
            user_note=listing.user_note,
            created_at=listing.created_at,
        ))

    return PaginatedListings(items=items, total=total, limit=limit, offset=offset)


@router.get("/{listing_id}", response_model=ListingDetailOut)
async def get_listing(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get full listing detail including images and pricing candidates."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.images), selectinload(Listing.pricing_candidates))
        .where(Listing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    image_outs = []
    for img in sorted(listing.images, key=lambda i: i.sort_order):
        file_url = f"/images/{listing.id}/{img.file_name}"
        thumb_url = img.thumb_path.replace("/data", "") if img.thumb_path else file_url
        image_outs.append({
            "id": img.id,
            "file_url": file_url,
            "thumb_url": thumb_url,
            "sort_order": img.sort_order,
        })

    candidate_outs = []
    for c in listing.pricing_candidates:
        candidate_outs.append({
            "source_title": c.source_title,
            "source_price": c.source_price,
            "source_price_type": c.source_price_type,
            "source_url": c.source_url,
            "similarity_score": c.similarity_score,
            "is_comparable": c.is_comparable,
        })

    return ListingDetailOut(
        id=listing.id,
        status=listing.status,
        title=listing.title,
        description=listing.description,
        item_name=listing.item_name,
        item_category=listing.item_category,
        item_condition=listing.item_condition,
        recommended_price=listing.recommended_price,
        final_price=listing.final_price,
        price_strategy=listing.price_strategy,
        price_confidence=listing.price_confidence,
        price_reasoning=listing.price_reasoning,
        comp_count=listing.comp_count,
        median_price=listing.median_price,
        price_range_low=listing.price_range_low,
        price_range_high=listing.price_range_high,
        ka_category_id=listing.ka_category_id,
        ka_location_zip=listing.ka_location_zip or "",
        ka_listing_url=listing.ka_listing_url,
        user_note=listing.user_note,
        identification_confidence=listing.identification_confidence,
        images=image_outs,
        pricing_candidates=candidate_outs,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )


@router.patch("/{listing_id}")
async def update_listing(
    listing_id: UUID,
    body: ListingUpdateIn,
    db: AsyncSession = Depends(get_db),
):
    """Update listing fields (used during review)."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    update_data = body.model_dump(exclude_unset=True)
    old_status = listing.status

    for field, value in update_data.items():
        setattr(listing, field, value)

    listing.updated_at = datetime.now(timezone.utc)

    # Set approved_at timestamp
    if body.status == "approved" and old_status != "approved":
        listing.approved_at = datetime.now(timezone.utc)
        # If no final_price set, use recommended_price
        if not listing.final_price:
            listing.final_price = listing.recommended_price

    # Audit log for status changes
    if body.status and body.status != old_status:
        db.add(AuditLog(
            listing_id=listing.id,
            event_type="status_change",
            old_value=old_status,
            new_value=body.status,
        ))

    await db.commit()

    return {"id": listing.id, "status": listing.status, "updated_at": listing.updated_at}


@router.post("/bulk-approve", response_model=BulkApproveOut)
async def bulk_approve(body: BulkApproveIn, db: AsyncSession = Depends(get_db)):
    """Approve all draft_ready listings matching filters."""
    query = select(Listing).where(Listing.status == "draft_ready")

    if body.filter and "min_price_confidence" in body.filter:
        confidence_order = {"high": 3, "medium": 2, "low": 1, "none": 0}
        min_conf = body.filter["min_price_confidence"]
        min_val = confidence_order.get(min_conf, 0)
        # Filter by confidence level
        allowed = [k for k, v in confidence_order.items() if v >= min_val]
        query = query.where(Listing.price_confidence.in_(allowed))

    result = await db.execute(query)
    listings = result.scalars().all()

    now = datetime.now(timezone.utc)
    approved_ids = []
    for listing in listings:
        listing.status = "approved"
        listing.approved_at = now
        listing.updated_at = now
        if not listing.final_price:
            listing.final_price = listing.recommended_price
        approved_ids.append(listing.id)

        db.add(AuditLog(
            listing_id=listing.id,
            event_type="status_change",
            old_value="draft_ready",
            new_value="approved",
            details={"source": "bulk_approve"},
        ))

    await db.commit()

    return BulkApproveOut(approved_count=len(approved_ids), listing_ids=approved_ids)
