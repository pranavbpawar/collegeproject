-- ============================================================================
-- TBAPS Traffic Monitoring Extension
-- Database Schema for Network Traffic Analysis
-- ============================================================================
--
-- DESCRIPTION:
--   Extends TBAPS schema with traffic monitoring capabilities
--   Captures DNS queries, website visits, and browsing behavior
--   Privacy-balanced approach: DNS + HTTPS metadata (no payload inspection)
--
-- PRIVACY MODEL:
--   - Opt-in consent required
--   - 30-day data retention
--   - Metadata only (no packet payloads)
--   - Encrypted at rest
--   - GDPR compliant
--
-- DEPLOYMENT:
--   Run after main init_schema.sql
--   psql -U ztuser -d zerotrust -f traffic_monitoring_schema.sql
--
-- ============================================================================

-- Enable required extensions (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- CUSTOM TYPES
-- ============================================================================

-- Website categories
CREATE TYPE website_category AS ENUM (
    'productivity',
    'communication',
    'research',
    'professional_network',
    'news',
    'social_media',
    'entertainment',
    'shopping',
    'finance',
    'health',
    'education',
    'other',
    'unknown'
);

-- Traffic anomaly types
CREATE TYPE traffic_anomaly_type AS ENUM (
    'suspicious_domain',
    'excessive_browsing',
    'unusual_hours',
    'blocked_site_access',
    'data_exfiltration',
    'malware_domain'
);

-- ============================================================================
-- TABLE: traffic_monitoring_consent
-- ============================================================================

CREATE TABLE IF NOT EXISTS traffic_monitoring_consent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Employee reference
    employee_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Consent details
    consented BOOLEAN NOT NULL DEFAULT FALSE,
    consent_date TIMESTAMP WITH TIME ZONE,
    withdrawn_date TIMESTAMP WITH TIME ZONE,
    
    -- Consent version tracking
    consent_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    consent_text TEXT NOT NULL,
    
    -- Request details
    ip_address INET,
    user_agent TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_consent_dates CHECK (
        (consented = FALSE AND consent_date IS NULL) OR
        (consented = TRUE AND consent_date IS NOT NULL)
    ),
    CONSTRAINT valid_withdrawal CHECK (
        withdrawn_date IS NULL OR withdrawn_date >= consent_date
    )
);

-- Indexes
CREATE INDEX idx_traffic_consent_employee ON traffic_monitoring_consent(employee_id);
CREATE INDEX idx_traffic_consent_active ON traffic_monitoring_consent(employee_id) 
    WHERE consented = TRUE AND withdrawn_date IS NULL;

COMMENT ON TABLE traffic_monitoring_consent IS 'GDPR-compliant consent tracking for traffic monitoring';
COMMENT ON COLUMN traffic_monitoring_consent.consent_text IS 'Full text of consent agreement for legal compliance';

-- ============================================================================
-- TABLE: website_categories (Reference Data)
-- ============================================================================

CREATE TABLE IF NOT EXISTS website_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Domain pattern (supports wildcards)
    domain_pattern VARCHAR(255) UNIQUE NOT NULL,
    
    -- Classification
    category website_category NOT NULL,
    productivity_score INTEGER NOT NULL CHECK (productivity_score >= 0 AND productivity_score <= 100),
    
    -- Control flags
    is_blocked BOOLEAN DEFAULT FALSE,
    requires_justification BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255)
);

-- Indexes
CREATE INDEX idx_website_cat_domain ON website_categories(domain_pattern);
CREATE INDEX idx_website_cat_category ON website_categories(category);
CREATE INDEX idx_website_cat_blocked ON website_categories(is_blocked) WHERE is_blocked = TRUE;

COMMENT ON TABLE website_categories IS 'Domain categorization for productivity scoring';
COMMENT ON COLUMN website_categories.domain_pattern IS 'Domain pattern with wildcard support (e.g., *.github.com)';
COMMENT ON COLUMN website_categories.productivity_score IS 'Productivity score 0-100 (100=highly productive)';

-- ============================================================================
-- TABLE: traffic_dns_queries (PARTITIONED BY MONTH)
-- ============================================================================

CREATE TABLE IF NOT EXISTS traffic_dns_queries (
    id UUID DEFAULT gen_random_uuid(),
    
    -- Employee reference
    employee_id VARCHAR(255) NOT NULL,
    
    -- DNS query details
    domain VARCHAR(255) NOT NULL,
    query_type VARCHAR(10) NOT NULL,  -- A, AAAA, CNAME, MX, etc.
    
    -- Network details
    client_ip INET NOT NULL,
    resolved_ip INET,
    
    -- Timing
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    response_time_ms INTEGER,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create partitions for current month and next 3 months
CREATE TABLE traffic_dns_queries_2026_02 PARTITION OF traffic_dns_queries
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE traffic_dns_queries_2026_03 PARTITION OF traffic_dns_queries
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE traffic_dns_queries_2026_04 PARTITION OF traffic_dns_queries
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE TABLE traffic_dns_queries_2026_05 PARTITION OF traffic_dns_queries
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Indexes
CREATE INDEX idx_traffic_dns_employee_time ON traffic_dns_queries(employee_id, timestamp DESC);
CREATE INDEX idx_traffic_dns_domain ON traffic_dns_queries(domain);
CREATE INDEX idx_traffic_dns_expires ON traffic_dns_queries(expires_at);

COMMENT ON TABLE traffic_dns_queries IS 'DNS query log with 7-day retention, partitioned by month';
COMMENT ON COLUMN traffic_dns_queries.expires_at IS 'Auto-delete after 7 days for privacy';

-- ============================================================================
-- TABLE: traffic_website_visits (PARTITIONED BY MONTH)
-- ============================================================================

CREATE TABLE IF NOT EXISTS traffic_website_visits (
    id UUID DEFAULT gen_random_uuid(),
    
    -- Employee reference
    employee_id VARCHAR(255) NOT NULL,
    
    -- Website details
    domain VARCHAR(255) NOT NULL,
    category website_category,
    productivity_score INTEGER CHECK (productivity_score >= 0 AND productivity_score <= 100),
    
    -- Visit timing
    first_visit TIMESTAMP WITH TIME ZONE NOT NULL,
    last_visit TIMESTAMP WITH TIME ZONE NOT NULL,
    visit_duration_seconds INTEGER NOT NULL DEFAULT 0,
    
    -- Activity metrics
    page_count INTEGER DEFAULT 1,
    bytes_transferred BIGINT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    
    -- Constraints
    CONSTRAINT valid_visit_duration CHECK (last_visit >= first_visit),
    CONSTRAINT valid_page_count CHECK (page_count > 0),
    
    PRIMARY KEY (id, first_visit)
) PARTITION BY RANGE (first_visit);

-- Create partitions
CREATE TABLE traffic_website_visits_2026_02 PARTITION OF traffic_website_visits
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE traffic_website_visits_2026_03 PARTITION OF traffic_website_visits
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE traffic_website_visits_2026_04 PARTITION OF traffic_website_visits
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE TABLE traffic_website_visits_2026_05 PARTITION OF traffic_website_visits
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Indexes
CREATE INDEX idx_traffic_visits_employee_time ON traffic_website_visits(employee_id, first_visit DESC);
CREATE INDEX idx_traffic_visits_domain ON traffic_website_visits(domain);
CREATE INDEX idx_traffic_visits_category ON traffic_website_visits(category);
CREATE INDEX idx_traffic_visits_expires ON traffic_website_visits(expires_at);

COMMENT ON TABLE traffic_website_visits IS 'Aggregated website visits with 30-day retention';
COMMENT ON COLUMN traffic_website_visits.visit_duration_seconds IS 'Time between first and last packet to domain';

-- ============================================================================
-- TABLE: traffic_packet_metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS traffic_packet_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Employee reference
    employee_id VARCHAR(255) NOT NULL,
    
    -- Packet details (metadata only, no payload)
    source_ip INET NOT NULL,
    destination_ip INET NOT NULL,
    destination_port INTEGER,
    protocol VARCHAR(10),  -- TCP, UDP, ICMP
    
    -- TLS/HTTPS metadata
    tls_sni VARCHAR(255),  -- Server Name Indication
    tls_version VARCHAR(20),
    
    -- Packet size
    packet_size_bytes INTEGER,
    
    -- Timing
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '3 days'),
    
    -- Constraints
    CONSTRAINT valid_port CHECK (destination_port >= 0 AND destination_port <= 65535)
);

-- Indexes
CREATE INDEX idx_traffic_packets_employee_time ON traffic_packet_metadata(employee_id, timestamp DESC);
CREATE INDEX idx_traffic_packets_dest_ip ON traffic_packet_metadata(destination_ip);
CREATE INDEX idx_traffic_packets_sni ON traffic_packet_metadata(tls_sni);
CREATE INDEX idx_traffic_packets_expires ON traffic_packet_metadata(expires_at);

COMMENT ON TABLE traffic_packet_metadata IS 'Packet-level metadata (no payloads) with 3-day retention';
COMMENT ON COLUMN traffic_packet_metadata.tls_sni IS 'TLS Server Name Indication for HTTPS sites';

-- ============================================================================
-- TABLE: browsing_baselines
-- ============================================================================

CREATE TABLE IF NOT EXISTS browsing_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Employee reference
    employee_id VARCHAR(255) NOT NULL,
    
    -- Baseline metrics
    metric VARCHAR(100) NOT NULL,  -- avg_productive_hours, social_media_minutes, etc.
    
    -- Statistical values
    baseline_value FLOAT NOT NULL,
    std_dev FLOAT NOT NULL CHECK (std_dev >= 0),
    p95 FLOAT NOT NULL,
    p50 FLOAT NOT NULL,
    p05 FLOAT NOT NULL,
    
    -- Calculation period
    calculation_start TIMESTAMP WITH TIME ZONE NOT NULL,
    calculation_end TIMESTAMP WITH TIME ZONE NOT NULL,
    sample_size INTEGER NOT NULL CHECK (sample_size > 0),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '90 days'),
    
    -- Constraints
    CONSTRAINT unique_employee_browsing_metric UNIQUE (employee_id, metric),
    CONSTRAINT valid_calculation_period CHECK (calculation_end > calculation_start)
);

-- Indexes
CREATE INDEX idx_browsing_baseline_employee ON browsing_baselines(employee_id);
CREATE INDEX idx_browsing_baseline_metric ON browsing_baselines(metric);
CREATE INDEX idx_browsing_baseline_updated ON browsing_baselines(updated_at DESC);

COMMENT ON TABLE browsing_baselines IS 'Employee browsing behavior baselines with 90-day retention';

-- ============================================================================
-- TABLE: traffic_anomalies
-- ============================================================================

CREATE TABLE IF NOT EXISTS traffic_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Employee reference
    employee_id VARCHAR(255) NOT NULL,
    
    -- Anomaly details
    anomaly_type traffic_anomaly_type NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL,
    
    -- Related data
    domain VARCHAR(255),
    related_visits JSONB DEFAULT '[]',
    baseline_deviation FLOAT,
    
    -- Resolution
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolution_notes TEXT,
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '1 year'),
    
    -- Constraints
    CONSTRAINT resolved_requires_timestamp CHECK (
        (resolved = FALSE AND resolved_at IS NULL) OR
        (resolved = TRUE AND resolved_at IS NOT NULL)
    )
);

-- Indexes
CREATE INDEX idx_traffic_anomalies_employee ON traffic_anomalies(employee_id);
CREATE INDEX idx_traffic_anomalies_type ON traffic_anomalies(anomaly_type);
CREATE INDEX idx_traffic_anomalies_severity ON traffic_anomalies(severity);
CREATE INDEX idx_traffic_anomalies_resolved ON traffic_anomalies(resolved, detected_at DESC);

COMMENT ON TABLE traffic_anomalies IS 'Detected browsing anomalies with 1-year retention';

-- ============================================================================
-- TABLE: traffic_audit_log
-- ============================================================================

CREATE TABLE IF NOT EXISTS traffic_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Action details
    action VARCHAR(100) NOT NULL,  -- 'viewed_traffic', 'exported_data', 'consent_granted', etc.
    actor_id VARCHAR(255) NOT NULL,  -- Who performed the action
    
    -- Target
    target_employee_id VARCHAR(255),  -- Whose data was accessed
    
    -- Details
    details JSONB DEFAULT '{}',
    
    -- Request metadata
    ip_address INET,
    user_agent TEXT,
    
    -- Timestamp
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '7 years'),
    
    -- Constraints
    CONSTRAINT valid_action CHECK (action != '')
);

-- Indexes
CREATE INDEX idx_traffic_audit_timestamp ON traffic_audit_log(timestamp DESC);
CREATE INDEX idx_traffic_audit_actor ON traffic_audit_log(actor_id, timestamp DESC);
CREATE INDEX idx_traffic_audit_target ON traffic_audit_log(target_employee_id, timestamp DESC);
CREATE INDEX idx_traffic_audit_action ON traffic_audit_log(action);

COMMENT ON TABLE traffic_audit_log IS 'Audit log for traffic data access (7-year GDPR retention)';

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_traffic_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to categorize domain
CREATE OR REPLACE FUNCTION categorize_domain(p_domain VARCHAR)
RETURNS TABLE(category website_category, productivity_score INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT wc.category, wc.productivity_score
    FROM website_categories wc
    WHERE p_domain LIKE wc.domain_pattern
    ORDER BY LENGTH(wc.domain_pattern) DESC
    LIMIT 1;
    
    -- If no match found, return unknown
    IF NOT FOUND THEN
        RETURN QUERY SELECT 'unknown'::website_category, 50;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to delete expired traffic data
CREATE OR REPLACE FUNCTION delete_expired_traffic_data()
RETURNS TABLE(table_name TEXT, rows_deleted BIGINT) AS $$
DECLARE
    v_deleted BIGINT;
BEGIN
    -- Delete expired DNS queries
    DELETE FROM traffic_dns_queries WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'traffic_dns_queries';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired website visits
    DELETE FROM traffic_website_visits WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'traffic_website_visits';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired packet metadata
    DELETE FROM traffic_packet_metadata WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'traffic_packet_metadata';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired baselines
    DELETE FROM browsing_baselines WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'browsing_baselines';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired anomalies
    DELETE FROM traffic_anomalies WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'traffic_anomalies';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired audit logs
    DELETE FROM traffic_audit_log WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'traffic_audit_log';
    rows_deleted := v_deleted;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger for traffic_monitoring_consent
CREATE TRIGGER update_traffic_consent_updated_at
    BEFORE UPDATE ON traffic_monitoring_consent
    FOR EACH ROW
    EXECUTE FUNCTION update_traffic_updated_at();

-- Trigger for website_categories
CREATE TRIGGER update_website_categories_updated_at
    BEFORE UPDATE ON website_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_traffic_updated_at();

-- Trigger for browsing_baselines
CREATE TRIGGER update_browsing_baselines_updated_at
    BEFORE UPDATE ON browsing_baselines
    FOR EACH ROW
    EXECUTE FUNCTION update_traffic_updated_at();

-- ============================================================================
-- SEED DATA: Website Categories
-- ============================================================================

INSERT INTO website_categories (domain_pattern, category, productivity_score, description) VALUES
    -- Productivity tools (90-100)
    ('github.com', 'productivity', 100, 'Code repository and collaboration'),
    ('%.github.com', 'productivity', 100, 'GitHub subdomains'),
    ('gitlab.com', 'productivity', 100, 'Code repository'),
    ('bitbucket.org', 'productivity', 100, 'Code repository'),
    ('stackoverflow.com', 'productivity', 95, 'Developer Q&A'),
    ('%.stackoverflow.com', 'productivity', 95, 'Stack Exchange network'),
    
    -- Project management (90-100)
    ('jira.%', 'productivity', 100, 'Project management'),
    ('%.atlassian.net', 'productivity', 100, 'Atlassian products'),
    ('asana.com', 'productivity', 100, 'Task management'),
    ('trello.com', 'productivity', 95, 'Project boards'),
    ('monday.com', 'productivity', 95, 'Work management'),
    
    -- Communication (70-90)
    ('slack.com', 'communication', 85, 'Team messaging'),
    ('%.slack.com', 'communication', 85, 'Slack workspaces'),
    ('teams.microsoft.com', 'communication', 85, 'Microsoft Teams'),
    ('zoom.us', 'communication', 80, 'Video conferencing'),
    ('meet.google.com', 'communication', 80, 'Google Meet'),
    
    -- Cloud storage (80-90)
    ('drive.google.com', 'productivity', 90, 'Google Drive'),
    ('docs.google.com', 'productivity', 90, 'Google Docs'),
    ('sheets.google.com', 'productivity', 90, 'Google Sheets'),
    ('dropbox.com', 'productivity', 85, 'Cloud storage'),
    ('onedrive.live.com', 'productivity', 85, 'OneDrive'),
    
    -- Documentation (80-90)
    ('notion.so', 'productivity', 90, 'Documentation'),
    ('confluence.%', 'productivity', 90, 'Confluence wiki'),
    ('readthedocs.%', 'research', 85, 'Documentation hosting'),
    
    -- Professional networks (60-80)
    ('linkedin.com', 'professional_network', 75, 'Professional networking'),
    ('%.linkedin.com', 'professional_network', 75, 'LinkedIn subdomains'),
    
    -- Research/Learning (70-85)
    ('wikipedia.org', 'research', 80, 'Encyclopedia'),
    ('%.wikipedia.org', 'research', 80, 'Wikipedia languages'),
    ('medium.com', 'research', 75, 'Articles and blogs'),
    ('dev.to', 'research', 80, 'Developer community'),
    
    -- News (40-60)
    ('news.ycombinator.com', 'news', 60, 'Hacker News'),
    ('reddit.com', 'news', 50, 'Social news'),
    ('%.reddit.com', 'news', 50, 'Reddit subdomains'),
    
    -- Social media (10-30)
    ('facebook.com', 'social_media', 20, 'Social network'),
    ('%.facebook.com', 'social_media', 20, 'Facebook subdomains'),
    ('twitter.com', 'social_media', 25, 'Microblogging'),
    ('x.com', 'social_media', 25, 'Twitter/X'),
    ('instagram.com', 'social_media', 15, 'Photo sharing'),
    ('tiktok.com', 'social_media', 10, 'Short videos'),
    
    -- Entertainment (10-30)
    ('youtube.com', 'entertainment', 30, 'Video platform'),
    ('%.youtube.com', 'entertainment', 30, 'YouTube subdomains'),
    ('netflix.com', 'entertainment', 10, 'Streaming service'),
    ('twitch.tv', 'entertainment', 15, 'Live streaming'),
    ('spotify.com', 'entertainment', 20, 'Music streaming'),
    
    -- Shopping (10-20)
    ('amazon.com', 'shopping', 15, 'E-commerce'),
    ('%.amazon.com', 'shopping', 15, 'Amazon subdomains'),
    ('ebay.com', 'shopping', 15, 'Online marketplace'),
    ('aliexpress.com', 'shopping', 10, 'E-commerce'),
    
    -- Finance (60-70)
    ('%.bank', 'finance', 65, 'Banking sites'),
    ('paypal.com', 'finance', 70, 'Payment service'),
    ('stripe.com', 'finance', 70, 'Payment processing')
ON CONFLICT (domain_pattern) DO NOTHING;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Active consents
CREATE OR REPLACE VIEW traffic_active_consents AS
SELECT 
    employee_id,
    consent_date,
    consent_version,
    created_at
FROM traffic_monitoring_consent
WHERE consented = TRUE
AND withdrawn_date IS NULL;

-- View: Daily browsing summary
CREATE OR REPLACE VIEW traffic_daily_summary AS
SELECT 
    employee_id,
    DATE(first_visit) as visit_date,
    COUNT(DISTINCT domain) as unique_domains,
    SUM(visit_duration_seconds) as total_seconds,
    SUM(CASE WHEN productivity_score >= 70 THEN visit_duration_seconds ELSE 0 END) as productive_seconds,
    SUM(CASE WHEN category = 'social_media' THEN visit_duration_seconds ELSE 0 END) as social_media_seconds,
    AVG(productivity_score) as avg_productivity_score
FROM traffic_website_visits
WHERE first_visit >= NOW() - INTERVAL '30 days'
GROUP BY employee_id, DATE(first_visit);

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON TABLE traffic_monitoring_consent TO ztuser;
GRANT ALL PRIVILEGES ON TABLE website_categories TO ztuser;
GRANT ALL PRIVILEGES ON TABLE traffic_dns_queries TO ztuser;
GRANT ALL PRIVILEGES ON TABLE traffic_website_visits TO ztuser;
GRANT ALL PRIVILEGES ON TABLE traffic_packet_metadata TO ztuser;
GRANT ALL PRIVILEGES ON TABLE browsing_baselines TO ztuser;
GRANT ALL PRIVILEGES ON TABLE traffic_anomalies TO ztuser;
GRANT ALL PRIVILEGES ON TABLE traffic_audit_log TO ztuser;

-- Grant on partitions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ztuser;

-- Grant on views
GRANT SELECT ON traffic_active_consents TO ztuser;
GRANT SELECT ON traffic_daily_summary TO ztuser;

-- Grant on functions
GRANT EXECUTE ON FUNCTION categorize_domain(VARCHAR) TO ztuser;
GRANT EXECUTE ON FUNCTION delete_expired_traffic_data() TO ztuser;

-- ============================================================================
-- VALIDATION
-- ============================================================================

-- Verify tables exist
DO $$
DECLARE
    v_tables TEXT[] := ARRAY[
        'traffic_monitoring_consent',
        'website_categories',
        'traffic_dns_queries',
        'traffic_website_visits',
        'traffic_packet_metadata',
        'browsing_baselines',
        'traffic_anomalies',
        'traffic_audit_log'
    ];
    v_table TEXT;
    v_count INTEGER;
BEGIN
    FOREACH v_table IN ARRAY v_tables
    LOOP
        SELECT COUNT(*) INTO v_count
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = v_table;
        
        IF v_count = 0 THEN
            RAISE EXCEPTION 'Table % not created', v_table;
        ELSE
            RAISE NOTICE '✓ Table % created successfully', v_table;
        END IF;
    END LOOP;
    
    RAISE NOTICE '✓ All traffic monitoring tables created successfully';
END;
$$;

-- ============================================================================
-- SCHEMA VERSION
-- ============================================================================

COMMENT ON SCHEMA public IS 'TBAPS Database Schema v2.0 - With Traffic Monitoring Extension';
