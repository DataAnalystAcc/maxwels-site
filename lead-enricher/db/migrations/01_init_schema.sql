-- Lead Enricher Schema Initialization
-- Creates the core entity tables mapped out in the implementation plan.

-- 1. companies
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_input_name VARCHAR NOT NULL,
    normalized_name VARCHAR NOT NULL,
    legal_name VARCHAR,
    website VARCHAR,
    main_phone VARCHAR,
    main_email VARCHAR,
    contact_page_url VARCHAR,
    industry VARCHAR,
    country VARCHAR,
    city VARCHAR,
    street VARCHAR,
    postal_code VARCHAR,
    linkedin_company_url VARCHAR,
    employee_count INTEGER,
    employee_count_status VARCHAR,
    revenue NUMERIC,
    revenue_currency VARCHAR,
    revenue_status VARCHAR,
    company_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. corporate_structure
CREATE TABLE IF NOT EXISTS corporate_structure (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    belongs_to_group BOOLEAN,
    parent_company_name VARCHAR,
    parent_company_website VARCHAR,
    parent_company_country VARCHAR,
    hq_germany_name VARCHAR,
    hq_germany_address VARCHAR,
    hq_eu_name VARCHAR,
    hq_eu_address VARCHAR,
    hq_global_name VARCHAR,
    hq_global_address VARCHAR,
    corporate_notes TEXT,
    confidence INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. sites
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    site_name VARCHAR NOT NULL,
    site_type VARCHAR,
    country VARCHAR,
    city VARCHAR,
    street VARCHAR,
    postal_code VARCHAR,
    phone VARCHAR,
    email VARCHAR,
    site_page_url VARCHAR,
    source_summary TEXT,
    confidence INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. news_items
CREATE TABLE IF NOT EXISTS news_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    title VARCHAR NOT NULL,
    source_name VARCHAR NOT NULL,
    source_url VARCHAR NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    summary TEXT,
    relevance_type VARCHAR,
    relevance_score INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. contacts
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    full_name VARCHAR NOT NULL,
    first_name VARCHAR,
    last_name VARCHAR,
    job_title VARCHAR,
    function_area VARCHAR,
    seniority VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    linkedin_url VARCHAR,
    linkedin_search_url VARCHAR,
    role_source VARCHAR,
    contact_status VARCHAR,
    confidence INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. sources
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR NOT NULL,
    entity_id UUID NOT NULL,
    source_type VARCHAR NOT NULL,
    source_name VARCHAR,
    source_url VARCHAR,
    extracted_field VARCHAR,
    extracted_value TEXT,
    confidence INTEGER,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. workflow_runs
CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id VARCHAR NOT NULL,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    step_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    payload_json JSONB
);

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_companies_normalized_name ON companies(normalized_name);
CREATE INDEX IF NOT EXISTS idx_sites_company_id ON sites(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_site_id ON contacts(site_id);
CREATE INDEX IF NOT EXISTS idx_sources_entity ON sources(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_batch ON workflow_runs(batch_id);
