"""Posting queue management router."""

import json
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import redis.asyncio as aioredis

from database import get_db
from models import Listing, ListingImage, PostingJob, AuditLog
from schemas import PostingStartIn, PostingStartOut, PostingResultIn
from config import settings

router = APIRouter(prefix="/api/posting", tags=["posting"])

POSTING_QUEUE_KEY = "posting_queue"


@router.post("/start", response_model=PostingStartOut)
async def start_posting(body: PostingStartIn, db: AsyncSession = Depends(get_db)):
    """Move approved listings into the posting queue."""
    if body.listing_ids:
        result = await db.execute(
            select(Listing).where(
                Listing.id.in_(body.listing_ids),
                Listing.status == "approved",
            )
        )
    else:
        result = await db.execute(
            select(Listing).where(Listing.status == "approved")
        )

    listings = result.scalars().all()
    if not listings:
        return PostingStartOut(queued_count=0, listing_ids=[])

    r = aioredis.from_url(settings.redis_url)
    now = datetime.now(timezone.utc)
    queued_ids = []

    for listing in listings:
        listing.status = "posting_queued"
        listing.updated_at = now

        # Create posting job record
        job = PostingJob(listing_id=listing.id, status="queued", attempt=1)
        db.add(job)

        # Enqueue to Redis
        job_payload = json.dumps({
            "listing_id": str(listing.id),
            "attempt": 1,
            "queued_at": now.isoformat(),
        })
        await r.rpush(POSTING_QUEUE_KEY, job_payload)

        # Audit log
        db.add(AuditLog(
            listing_id=listing.id,
            event_type="status_change",
            old_value="approved",
            new_value="posting_queued",
        ))

        queued_ids.append(listing.id)

    await r.close()
    await db.commit()

    return PostingStartOut(queued_count=len(queued_ids), listing_ids=queued_ids)


@router.get("/{listing_id}/posting-payload")
async def get_posting_payload(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all data needed by the posting worker to fill the Kleinanzeigen form."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.images))
        .where(Listing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    images = sorted(listing.images, key=lambda i: i.sort_order)

    return {
        "listing_id": str(listing.id),
        "title": listing.title,
        "description": listing.description,
        "price": float(listing.final_price or listing.recommended_price or 0),
        "category_id": listing.ka_category_id,
        "zip_code": listing.ka_location_zip or settings.default_zip,
        "condition": listing.item_condition,
        "images": [
            {"path": img.file_path, "name": img.file_name}
            for img in images
        ],
    }


@router.patch("/{listing_id}/posting-result")
async def update_posting_result(
    listing_id: UUID,
    body: PostingResultIn,
    db: AsyncSession = Depends(get_db),
):
    """Called by the posting worker to report success or failure."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    now = datetime.now(timezone.utc)

    if body.status == "posted":
        listing.status = "posted"
        listing.ka_listing_url = body.url
        listing.posted_at = now
        listing.last_posting_screenshot = body.screenshot_path
    elif body.status == "failed":
        listing.posting_attempts = body.attempt
        listing.last_posting_error = body.error_message
        listing.last_posting_screenshot = body.screenshot_path

        if body.attempt < 3:
            listing.status = "posting_failed"
            # Re-enqueue with incremented attempt
            r = aioredis.from_url(settings.redis_url)
            job_payload = json.dumps({
                "listing_id": str(listing.id),
                "attempt": body.attempt + 1,
                "queued_at": now.isoformat(),
            })
            await r.rpush(POSTING_QUEUE_KEY, job_payload)
            await r.close()
        else:
            listing.status = "failed_permanent"

    listing.updated_at = now

    # Create posting job record
    db.add(PostingJob(
        listing_id=listing.id,
        status="completed" if body.status == "posted" else "failed",
        attempt=body.attempt,
        started_at=now,
        completed_at=now,
        error_message=body.error_message,
        screenshot_path=body.screenshot_path,
        result_url=body.url,
    ))

    # Audit log
    db.add(AuditLog(
        listing_id=listing.id,
        event_type="posting_attempt",
        new_value=body.status,
        details={
            "attempt": body.attempt,
            "url": body.url,
            "error": body.error_message,
        },
    ))

    await db.commit()

    return {"listing_id": str(listing.id), "status": listing.status}
