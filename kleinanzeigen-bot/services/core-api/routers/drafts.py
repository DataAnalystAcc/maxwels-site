"""Draft generation router — triggers the identification + pricing pipeline."""

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import DraftGenerateIn, DraftGenerateOut
from services.identifier import generate_draft

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

    return DraftGenerateOut(
        success=result.get("success", False),
        listing_id=body.listing_id,
        title=result.get("title"),
        recommended_price=result.get("recommended_price"),
        price_confidence=result.get("price_confidence"),
        status=result.get("status", "draft_failed"),
        error=result.get("error"),
    )
