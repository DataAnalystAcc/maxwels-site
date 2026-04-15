-- Kleinanzeigen Bot — Schema Initialization
-- Creates all core tables for the listing automation system.

-- ============================================================
-- 1. listings — core entity, one row per item
-- ============================================================
CREATE TABLE IF NOT EXISTS listings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status              VARCHAR(30) NOT NULL DEFAULT 'intake_received',

    -- User input
    user_note           TEXT,
    telegram_chat_id    BIGINT NOT NULL,
    telegram_msg_ids    INTEGER[],
    media_group_id      VARCHAR(100),

    -- LLM-generated draft
    item_name           VARCHAR(255),
    item_category       VARCHAR(100),
    item_condition      VARCHAR(30),
    search_terms        VARCHAR(255)[],

    -- Listing content
    title               VARCHAR(120),
    description         TEXT,

    -- Pricing
    recommended_price   NUMERIC(10,2),
    final_price         NUMERIC(10,2),
    price_strategy      VARCHAR(20) DEFAULT 'competitive',
    price_confidence    VARCHAR(10),
    price_reasoning     TEXT,
    comp_count          INTEGER DEFAULT 0,
    median_price        NUMERIC(10,2),
    price_range_low     NUMERIC(10,2),
    price_range_high    NUMERIC(10,2),

    -- Kleinanzeigen posting
    ka_category_id      INTEGER,
    ka_location_zip     VARCHAR(10),
    ka_listing_url      VARCHAR(500),

    -- Posting metadata
    posting_attempts    INTEGER DEFAULT 0,
    last_posting_error  TEXT,
    last_posting_screenshot VARCHAR(500),

    -- Identification metadata
    identification_confidence VARCHAR(10),
    llm_model_used      VARCHAR(100),
    llm_raw_response    JSONB,

    -- Timestamps
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at         TIMESTAMP WITH TIME ZONE,
    posted_at           TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_created ON listings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_listings_chat ON listings(telegram_chat_id);


-- ============================================================
-- 2. listing_images — photos per item
-- ============================================================
CREATE TABLE IF NOT EXISTS listing_images (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id              UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,

    file_path               VARCHAR(500) NOT NULL,
    file_name               VARCHAR(255) NOT NULL,
    file_size_bytes         INTEGER,
    mime_type               VARCHAR(50),
    width                   INTEGER,
    height                  INTEGER,
    sort_order              INTEGER NOT NULL DEFAULT 0,

    -- Telegram metadata
    telegram_file_id        VARCHAR(200),
    telegram_file_unique_id VARCHAR(200),

    -- Resized copy for LLM
    thumb_path              VARCHAR(500),

    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_listing_images_listing ON listing_images(listing_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_listing_images_unique_file
    ON listing_images(telegram_file_unique_id);


-- ============================================================
-- 3. pricing_candidates — comparables from search
-- ============================================================
CREATE TABLE IF NOT EXISTS pricing_candidates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id          UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,

    source              VARCHAR(20) NOT NULL DEFAULT 'kleinanzeigen',
    source_url          VARCHAR(500),
    source_title        VARCHAR(255),
    source_price        NUMERIC(10,2),
    source_price_type   VARCHAR(20),       -- fixed / vb / free
    source_condition    VARCHAR(30),
    source_location     VARCHAR(100),
    source_posted_date  DATE,

    is_comparable       BOOLEAN DEFAULT true,
    similarity_score    NUMERIC(3,2),

    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pricing_candidates_listing ON pricing_candidates(listing_id);


-- ============================================================
-- 4. posting_jobs — tracks each posting attempt
-- ============================================================
CREATE TABLE IF NOT EXISTS posting_jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id          UUID NOT NULL REFERENCES listings(id),

    status              VARCHAR(20) NOT NULL DEFAULT 'queued',
    attempt             INTEGER NOT NULL DEFAULT 1,

    started_at          TIMESTAMP WITH TIME ZONE,
    completed_at        TIMESTAMP WITH TIME ZONE,
    error_message       TEXT,
    screenshot_path     VARCHAR(500),
    result_url          VARCHAR(500),

    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_posting_jobs_status ON posting_jobs(status);
CREATE INDEX IF NOT EXISTS idx_posting_jobs_listing ON posting_jobs(listing_id);


-- ============================================================
-- 5. audit_log — event log for debugging and traceability
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id          UUID REFERENCES listings(id) ON DELETE SET NULL,

    event_type          VARCHAR(50) NOT NULL,
    old_value           TEXT,
    new_value           TEXT,
    details             JSONB,

    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_listing ON audit_log(listing_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);


-- ============================================================
-- 6. settings — key-value config store
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    key                 VARCHAR(100) PRIMARY KEY,
    value               TEXT NOT NULL,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
