"""Pydantic schemas for request/response validation."""

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Listing Schemas ──────────────────────────────────────────

class ListingImageOut(BaseModel):
    id: UUID
    file_url: str
    thumb_url: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class PricingCandidateOut(BaseModel):
    source_title: Optional[str] = None
    source_price: Optional[Decimal] = None
    source_price_type: Optional[str] = None
    source_url: Optional[str] = None
    similarity_score: Optional[Decimal] = None
    is_comparable: bool = True

    class Config:
        from_attributes = True


class ListingSummaryOut(BaseModel):
    """Lightweight listing for the queue view."""
    id: UUID
    status: str
    title: Optional[str] = None
    item_name: Optional[str] = None
    item_category: Optional[str] = None
    item_condition: Optional[str] = None
    recommended_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    price_confidence: Optional[str] = None
    identification_confidence: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_count: int = 0
    user_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ListingDetailOut(BaseModel):
    """Full listing detail for the review panel."""
    id: UUID
    status: str
    title: Optional[str] = None
    description: Optional[str] = None
    item_name: Optional[str] = None
    item_category: Optional[str] = None
    item_condition: Optional[str] = None
    recommended_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    price_strategy: Optional[str] = None
    price_confidence: Optional[str] = None
    price_reasoning: Optional[str] = None
    comp_count: int = 0
    median_price: Optional[Decimal] = None
    price_range_low: Optional[Decimal] = None
    price_range_high: Optional[Decimal] = None
    ka_category_id: Optional[int] = None
    ka_location_zip: Optional[str] = None
    ka_listing_url: Optional[str] = None
    user_note: Optional[str] = None
    identification_confidence: Optional[str] = None
    images: list[ListingImageOut] = []
    pricing_candidates: list[PricingCandidateOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ListingUpdateIn(BaseModel):
    """Fields that can be edited during review."""
    title: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    final_price: Optional[Decimal] = None
    item_condition: Optional[str] = None
    ka_category_id: Optional[int] = None
    ka_location_zip: Optional[str] = None
    status: Optional[Literal[
        "approved", "rejected", "draft_ready", "skipped"
    ]] = None


# ── Draft Generation Schemas ─────────────────────────────────

class DraftGenerateIn(BaseModel):
    listing_id: UUID


class DraftGenerateOut(BaseModel):
    success: bool
    listing_id: UUID
    title: Optional[str] = None
    recommended_price: Optional[Decimal] = None
    price_confidence: Optional[str] = None
    status: str
    error: Optional[str] = None


# ── LLM Response Schemas ─────────────────────────────────────

class IdentificationResult(BaseModel):
    """Expected structured JSON output from the LLM."""
    item_name: str = Field(max_length=255)
    item_category: str = Field(max_length=100)
    item_condition: Literal["new", "like_new", "good", "fair", "poor"]
    search_terms: list[str] = Field(min_length=1, max_length=5)
    title: str = Field(max_length=120)
    description: str = Field(max_length=2000)
    identification_confidence: Literal["high", "medium", "low"]


# ── Bulk Actions ─────────────────────────────────────────────

class BulkApproveIn(BaseModel):
    filter: Optional[dict] = None  # e.g. {"status": "draft_ready", "min_price_confidence": "high"}


class BulkApproveOut(BaseModel):
    approved_count: int
    listing_ids: list[UUID]


# ── Posting Schemas ──────────────────────────────────────────

class PostingStartIn(BaseModel):
    listing_ids: Optional[list[UUID]] = None  # if empty, queue all approved


class PostingStartOut(BaseModel):
    queued_count: int
    listing_ids: list[UUID]


class PostingResultIn(BaseModel):
    status: Literal["posted", "failed"]
    url: Optional[str] = None
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    attempt: int = 1


# ── Pagination ───────────────────────────────────────────────

class PaginatedListings(BaseModel):
    items: list[ListingSummaryOut]
    total: int
    limit: int
    offset: int
