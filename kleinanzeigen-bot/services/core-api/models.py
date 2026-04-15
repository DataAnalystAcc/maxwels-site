"""SQLAlchemy ORM models for the Kleinanzeigen Bot."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean, Numeric, DateTime,
    ForeignKey, Index, ARRAY, JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Listing(Base):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(30), nullable=False, default="intake_received")

    # User input
    user_note = Column(Text)
    telegram_chat_id = Column(BigInteger, nullable=False)
    telegram_msg_ids = Column(ARRAY(Integer))
    media_group_id = Column(String(100))

    # LLM-generated draft
    item_name = Column(String(255))
    item_category = Column(String(100))
    item_condition = Column(String(30))
    search_terms = Column(ARRAY(String(255)))

    # Listing content
    title = Column(String(120))
    description = Column(Text)

    # Pricing
    recommended_price = Column(Numeric(10, 2))
    final_price = Column(Numeric(10, 2))
    price_strategy = Column(String(20), default="competitive")
    price_confidence = Column(String(10))
    price_reasoning = Column(Text)
    comp_count = Column(Integer, default=0)
    median_price = Column(Numeric(10, 2))
    price_range_low = Column(Numeric(10, 2))
    price_range_high = Column(Numeric(10, 2))

    # Kleinanzeigen posting
    ka_category_id = Column(Integer)
    ka_location_zip = Column(String(10))
    ka_listing_url = Column(String(500))

    # Posting metadata
    posting_attempts = Column(Integer, default=0)
    last_posting_error = Column(Text)
    last_posting_screenshot = Column(String(500))

    # Identification metadata
    identification_confidence = Column(String(10))
    llm_model_used = Column(String(100))
    llm_raw_response = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime(timezone=True))
    posted_at = Column(DateTime(timezone=True))

    # Relationships
    images = relationship("ListingImage", back_populates="listing",
                          order_by="ListingImage.sort_order", cascade="all, delete-orphan")
    pricing_candidates = relationship("PricingCandidate", back_populates="listing",
                                      cascade="all, delete-orphan")
    posting_jobs = relationship("PostingJob", back_populates="listing")


class ListingImage(Base):
    __tablename__ = "listing_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"),
                        nullable=False)

    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer)
    mime_type = Column(String(50))
    width = Column(Integer)
    height = Column(Integer)
    sort_order = Column(Integer, nullable=False, default=0)

    telegram_file_id = Column(String(200))
    telegram_file_unique_id = Column(String(200))

    thumb_path = Column(String(500))

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    listing = relationship("Listing", back_populates="images")


class PricingCandidate(Base):
    __tablename__ = "pricing_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"),
                        nullable=False)

    source = Column(String(20), nullable=False, default="kleinanzeigen")
    source_url = Column(String(500))
    source_title = Column(String(255))
    source_price = Column(Numeric(10, 2))
    source_price_type = Column(String(20))
    source_condition = Column(String(30))
    source_location = Column(String(100))
    source_posted_date = Column(DateTime)

    is_comparable = Column(Boolean, default=True)
    similarity_score = Column(Numeric(3, 2))

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    listing = relationship("Listing", back_populates="pricing_candidates")


class PostingJob(Base):
    __tablename__ = "posting_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)

    status = Column(String(20), nullable=False, default="queued")
    attempt = Column(Integer, nullable=False, default=1)

    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    screenshot_path = Column(String(500))
    result_url = Column(String(500))

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    listing = relationship("Listing", back_populates="posting_jobs")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="SET NULL"))

    event_type = Column(String(50), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    details = Column(JSONB)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
