"""Draft generation router — triggers the identification + pricing pipeline."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from database import get_db
from models import Listing
from schemas import DraftGenerateIn, DraftGenerateOut
from services.identifier import generate_draft
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


@router.post("/generate", response_model=DraftGenerateOut)
async def generate_draft_endpoint(
    body: DraftGenerateIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger draft generation for a listing.
    Called by n8n after Telegram intake completes.
    """
    result = await generate_draft(body.listing_id, db)

    # Notify the user on Telegram when the draft is ready
    if result.get("success") and settings.telegram_bot_token:
        try:
            listing_result = await db.execute(
                select(Listing.telegram_chat_id, Listing.title).where(Listing.id == body.listing_id)
            )
            row = listing_result.first()
            if row and row.telegram_chat_id:
                title = result.get("title") or "?"
                price = result.get("recommended_price")
                confidence = result.get("price_confidence", "")
                price_str = f"€{price:.0f}" if price else "N/A"
                msg = (
                    f"✅ *Draft ready!*\n\n"
                    f"*{title}*\n"
                    f"Suggested price: {price_str} ({confidence} confidence)\n\n"
                    f"Review: {settings.review_base_url}/review"
                )
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                        json={
                            "chat_id": row.telegram_chat_id,
                            "text": msg,
                            "parse_mode": "Markdown",
                        },
                    )
        except Exception as e:
            logger.warning(f"Failed to send draft-ready Telegram notification: {e}")

    return DraftGenerateOut(
        success=result.get("success", False),
        listing_id=body.listing_id,
        title=result.get("title"),
        recommended_price=result.get("recommended_price"),
        price_confidence=result.get("price_confidence"),
        status=result.get("status", "draft_failed"),
        error=result.get("error"),
    )
