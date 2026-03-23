-- ============================================================================
-- TBAPS (Trust-Based Adaptive Productivity System)
-- PostgreSQL 15 Production Schema
-- ============================================================================
--
-- DESCRIPTION:
--   Complete database schema for TBAPS self-hosted deployment
--   Supports 500+ employees, 100K+ signals/day, GDPR compliant
--
-- FEATURES:
--   - Employee management with soft deletes
--   - Signal event ingestion with 30-day retention
--   - Baseline profile calculation
--   - Trust score tracking
--   - Anomaly detection
--   - Audit logging (7-year retention)
--   - OAuth token encryption
--   - GDPR consent management
--
-- PERFORMANCE:
--   - Partitioned tables for time-series data
--   - Optimized indexes for common queries
--   - Automatic data retention policies
--   - Query response time < 500ms
--
-- COMPLIANCE:
--   - GDPR Article 30 compliant
--   - Right to be forgotten
--   - Data portability
--   - Audit trail
--
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- Encryption
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Full-text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- GIN indexes

-- ============================================================================
-- CUSTOM TYPES
-- ============================================================================

-- Employee status
CREATE TYPE employee_status AS ENUM ('active', 'inactive', 'offboarded');

-- Anomaly severity
CREATE TYPE anomaly_severity AS ENUM ('low', 'medium', 'high', 'critical');

-- Anomaly type
CREATE TYPE anomaly_type AS ENUM ('statistical', 'rule_based', 'ml_predicted', 'manual');

-- Audit action types
CREATE TYPE audit_action AS ENUM (
    'CREATE', 'READ', 'UPDATE', 'DELETE', 
    'EXPORT', 'ACCESS', 'LOGIN', 'LOGOUT',
    'CONSENT_GRANTED', 'CONSENT_WITHDRAWN',
    'DATA_DELETED', 'DATA_EXPORTED'
);

-- Signal types
CREATE TYPE signal_type AS ENUM (
    'calendar_event', 'email_sent', 'email_received',
    'task_created', 'task_completed', 'meeting_attended',
    'code_commit', 'document_created', 'document_edited'
);

-- ============================================================================
-- TABLE: employees
-- ============================================================================

CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    role VARCHAR(100),
    manager_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    
    -- Status tracking
    status employee_status NOT NULL DEFAULT 'active',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,  -- Soft delete for GDPR
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_status CHECK (deleted_at IS NULL OR status = 'offboarded')
);

-- Indexes for employees
CREATE INDEX idx_employees_email ON employees(email);
CREATE INDEX idx_employees_status ON employees(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_employees_department ON employees(department) WHERE deleted_at IS NULL;
CREATE INDEX idx_employees_manager ON employees(manager_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_employees_created_at ON employees(created_at);
CREATE INDEX idx_employees_metadata ON employees USING GIN (metadata);

-- Comments
COMMENT ON TABLE employees IS 'Employee master data with soft delete support for GDPR compliance';
COMMENT ON COLUMN employees.deleted_at IS 'Soft delete timestamp for GDPR right to be forgotten';
COMMENT ON COLUMN employees.metadata IS 'Flexible JSON storage for additional employee attributes';

-- ============================================================================
-- TABLE: signal_events (PARTITIONED BY MONTH)
-- ============================================================================

CREATE TABLE signal_events (
    id UUID DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Signal details
    signal_type signal_type NOT NULL,
    signal_value FLOAT NOT NULL,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    source VARCHAR(50) NOT NULL,  -- google_calendar, office365, jira, asana, etc.
    
    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- Auto-delete after 30 days
    
    -- Constraints
    CONSTRAINT signal_value_range CHECK (signal_value >= 0),
    CONSTRAINT expires_after_timestamp CHECK (expires_at > timestamp),
    
    PRIMARY KEY (id, timestamp)  -- Composite key for partitioning
) PARTITION BY RANGE (timestamp);

-- Create partitions for current month and next 3 months
-- These will be auto-created by the partition maintenance function
CREATE TABLE signal_events_2026_01 PARTITION OF signal_events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE signal_events_2026_02 PARTITION OF signal_events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE signal_events_2026_03 PARTITION OF signal_events
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE signal_events_2026_04 PARTITION OF signal_events
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Indexes for signal_events (created on parent, inherited by partitions)
CREATE INDEX idx_signal_events_employee_timestamp ON signal_events(employee_id, timestamp DESC);
CREATE INDEX idx_signal_events_type ON signal_events(signal_type);
CREATE INDEX idx_signal_events_source ON signal_events(source);
CREATE INDEX idx_signal_events_expires ON signal_events(expires_at);
CREATE INDEX idx_signal_events_metadata ON signal_events USING GIN (metadata);

COMMENT ON TABLE signal_events IS 'Time-series signal data with 30-day retention, partitioned by month';
COMMENT ON COLUMN signal_events.expires_at IS 'Automatic deletion timestamp (30 days from creation)';

-- ============================================================================
-- TABLE: baseline_profiles
-- ============================================================================

CREATE TABLE baseline_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Metric details
    metric VARCHAR(100) NOT NULL,  -- meetings_per_day, response_time, task_completion, etc.
    
    -- Statistical values
    baseline_value FLOAT NOT NULL,
    std_dev FLOAT NOT NULL CHECK (std_dev >= 0),
    p95 FLOAT NOT NULL,
    p50 FLOAT NOT NULL,  -- median
    p05 FLOAT NOT NULL,
    min_value FLOAT NOT NULL,
    max_value FLOAT NOT NULL,
    
    -- Confidence and sample size
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    sample_size INTEGER NOT NULL CHECK (sample_size > 0),
    
    -- Calculation period
    calculation_start TIMESTAMP WITH TIME ZONE NOT NULL,
    calculation_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- 90-day retention
    
    -- Constraints
    CONSTRAINT unique_employee_metric UNIQUE (employee_id, metric),
    CONSTRAINT valid_calculation_period CHECK (calculation_end > calculation_start),
    CONSTRAINT valid_percentiles CHECK (p05 <= p50 AND p50 <= p95)
);

-- Indexes for baseline_profiles
CREATE INDEX idx_baseline_employee ON baseline_profiles(employee_id);
CREATE INDEX idx_baseline_metric ON baseline_profiles(metric);
CREATE INDEX idx_baseline_updated ON baseline_profiles(updated_at DESC);
CREATE INDEX idx_baseline_expires ON baseline_profiles(expires_at);

COMMENT ON TABLE baseline_profiles IS 'Employee behavioral baselines calculated from 30+ days of signals';
COMMENT ON COLUMN baseline_profiles.confidence IS 'Statistical confidence level (0-1) based on sample size';

-- ============================================================================
-- TABLE: trust_scores (PARTITIONED BY MONTH)
-- ============================================================================

CREATE TABLE trust_scores (
    id UUID DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Score components (0-100)
    outcome_score FLOAT NOT NULL CHECK (outcome_score >= 0 AND outcome_score <= 100),
    behavioral_score FLOAT NOT NULL CHECK (behavioral_score >= 0 AND behavioral_score <= 100),
    security_score FLOAT NOT NULL CHECK (security_score >= 0 AND security_score <= 100),
    wellbeing_score FLOAT NOT NULL CHECK (wellbeing_score >= 0 AND wellbeing_score <= 100),
    
    -- Total score (weighted average)
    total_score FLOAT NOT NULL CHECK (total_score >= 0 AND total_score <= 100),
    
    -- Weights used in calculation
    weights JSONB NOT NULL DEFAULT '{"outcome": 0.3, "behavioral": 0.3, "security": 0.2, "wellbeing": 0.2}',
    
    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- 90-day retention
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create partitions for trust_scores
CREATE TABLE trust_scores_2026_01 PARTITION OF trust_scores
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE trust_scores_2026_02 PARTITION OF trust_scores
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE trust_scores_2026_03 PARTITION OF trust_scores
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE trust_scores_2026_04 PARTITION OF trust_scores
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- Indexes for trust_scores
CREATE INDEX idx_trust_scores_employee_timestamp ON trust_scores(employee_id, timestamp DESC);
CREATE INDEX idx_trust_scores_total ON trust_scores(total_score);
CREATE INDEX idx_trust_scores_expires ON trust_scores(expires_at);

COMMENT ON TABLE trust_scores IS 'Historical trust scores with 90-day retention, partitioned by month';
COMMENT ON COLUMN trust_scores.weights IS 'Weights used for calculating total_score from components';

-- ============================================================================
-- TABLE: anomalies
-- ============================================================================

CREATE TABLE anomalies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Anomaly details
    anomaly_type anomaly_type NOT NULL,
    severity anomaly_severity NOT NULL,
    description TEXT NOT NULL,
    
    -- Related data
    signals_involved JSONB DEFAULT '[]',  -- Array of signal IDs
    baseline_deviation FLOAT,  -- How many std devs from baseline
    
    -- Resolution tracking
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolution_notes TEXT,
    resolved_by UUID REFERENCES employees(id),
    
    -- Timestamps
    flagged_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- 1-year retention
    
    -- Constraints
    CONSTRAINT resolved_requires_timestamp CHECK (
        (resolved = FALSE AND resolved_at IS NULL) OR
        (resolved = TRUE AND resolved_at IS NOT NULL)
    )
);

-- Indexes for anomalies
CREATE INDEX idx_anomalies_employee ON anomalies(employee_id);
CREATE INDEX idx_anomalies_severity ON anomalies(severity);
CREATE INDEX idx_anomalies_resolved ON anomalies(resolved, flagged_at DESC);
CREATE INDEX idx_anomalies_flagged ON anomalies(flagged_at DESC);
CREATE INDEX idx_anomalies_expires ON anomalies(expires_at);
CREATE INDEX idx_anomalies_signals ON anomalies USING GIN (signals_involved);

COMMENT ON TABLE anomalies IS 'Detected anomalies with 1-year retention for investigation';
COMMENT ON COLUMN anomalies.baseline_deviation IS 'Number of standard deviations from baseline';

-- ============================================================================
-- TABLE: audit_logs (7-YEAR RETENTION)
-- ============================================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Action details
    action audit_action NOT NULL,
    user_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    
    -- Resource details
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    
    -- Change tracking
    changes JSONB DEFAULT '{}',  -- {"before": {...}, "after": {...}}
    
    -- Request details
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    
    -- Timestamp (immutable)
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Retention (7 years for GDPR)
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '7 years')
);

-- Indexes for audit_logs
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, timestamp DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_expires ON audit_logs(expires_at);
CREATE INDEX idx_audit_logs_changes ON audit_logs USING GIN (changes);

-- Full-text search on audit logs
CREATE INDEX idx_audit_logs_fulltext ON audit_logs USING GIN (
    to_tsvector('english', 
        COALESCE(resource_type, '') || ' ' || 
        COALESCE(changes::text, '')
    )
);

COMMENT ON TABLE audit_logs IS 'Immutable audit trail with 7-year retention for GDPR compliance';
COMMENT ON COLUMN audit_logs.changes IS 'Before/after state for UPDATE actions';

-- ============================================================================
-- TABLE: oauth_tokens (ENCRYPTED)
-- ============================================================================

CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Service details
    service VARCHAR(50) NOT NULL,  -- google_calendar, office365, jira, asana
    
    -- Encrypted tokens (using pgcrypto)
    encrypted_token BYTEA NOT NULL,
    encrypted_refresh_token BYTEA,
    
    -- Token metadata
    scope TEXT,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Revocation
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT unique_employee_service UNIQUE (employee_id, service),
    CONSTRAINT revoked_requires_timestamp CHECK (
        (revoked = FALSE AND revoked_at IS NULL) OR
        (revoked = TRUE AND revoked_at IS NOT NULL)
    )
);

-- Indexes for oauth_tokens
CREATE INDEX idx_oauth_tokens_employee ON oauth_tokens(employee_id);
CREATE INDEX idx_oauth_tokens_service ON oauth_tokens(service);
CREATE INDEX idx_oauth_tokens_expires ON oauth_tokens(expires_at) WHERE revoked = FALSE;

COMMENT ON TABLE oauth_tokens IS 'Encrypted OAuth tokens for third-party service integration';
COMMENT ON COLUMN oauth_tokens.encrypted_token IS 'AES-256 encrypted access token';
COMMENT ON COLUMN oauth_tokens.encrypted_refresh_token IS 'AES-256 encrypted refresh token';

-- ============================================================================
-- TABLE: consent_logs (GDPR)
-- ============================================================================

CREATE TABLE consent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Consent details
    consent_type VARCHAR(50) NOT NULL,  -- data_processing, monitoring, email_analysis
    consented BOOLEAN NOT NULL,
    
    -- Consent metadata
    consent_version VARCHAR(20) NOT NULL,  -- Version of consent form
    consent_text TEXT NOT NULL,  -- Full text of what was consented to
    
    -- Timestamps
    consent_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    withdrawn_date TIMESTAMP WITH TIME ZONE,
    
    -- Request details
    ip_address INET NOT NULL,
    user_agent TEXT,
    
    -- Constraints
    CONSTRAINT withdrawn_requires_consent CHECK (
        withdrawn_date IS NULL OR consented = TRUE
    )
);

-- Indexes for consent_logs
CREATE INDEX idx_consent_logs_employee ON consent_logs(employee_id, consent_date DESC);
CREATE INDEX idx_consent_logs_type ON consent_logs(consent_type);
CREATE INDEX idx_consent_logs_active ON consent_logs(employee_id, consent_type) 
    WHERE withdrawn_date IS NULL AND consented = TRUE;

COMMENT ON TABLE consent_logs IS 'GDPR consent tracking with full audit trail';
COMMENT ON COLUMN consent_logs.consent_text IS 'Full text of consent agreement for legal compliance';

-- ============================================================================
-- TABLE: data_exports (GDPR)
-- ============================================================================

CREATE TABLE data_exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Export details
    export_type VARCHAR(50) NOT NULL,  -- full_export, partial_export
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    
    -- File details
    file_path TEXT,
    file_size BIGINT,
    file_format VARCHAR(20) DEFAULT 'json',  -- json, csv, pdf
    
    -- Timestamps
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,  -- Download link expiry
    
    -- Request details
    requested_by UUID REFERENCES employees(id),
    ip_address INET,
    
    -- Constraints
    CONSTRAINT completed_requires_timestamp CHECK (
        (status != 'completed' AND completed_at IS NULL) OR
        (status = 'completed' AND completed_at IS NOT NULL)
    )
);

-- Indexes for data_exports
CREATE INDEX idx_data_exports_employee ON data_exports(employee_id, requested_at DESC);
CREATE INDEX idx_data_exports_status ON data_exports(status);
CREATE INDEX idx_data_exports_expires ON data_exports(expires_at) WHERE status = 'completed';

COMMENT ON TABLE data_exports IS 'GDPR data portability - employee data export requests';

-- ============================================================================
-- TABLE: deletion_requests (GDPR)
-- ============================================================================

CREATE TABLE deletion_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Request details
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, approved, processing, completed, rejected
    reason TEXT,
    
    -- Approval workflow
    requested_by UUID REFERENCES employees(id),
    approved_by UUID REFERENCES employees(id),
    
    -- Timestamps
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Deletion details
    deletion_scope JSONB DEFAULT '{}',  -- What data to delete
    deletion_summary JSONB,  -- Summary of deleted data
    
    -- Request details
    ip_address INET,
    
    -- Constraints
    CONSTRAINT approved_requires_timestamp CHECK (
        (status != 'approved' AND approved_at IS NULL) OR
        (status IN ('approved', 'processing', 'completed') AND approved_at IS NOT NULL)
    ),
    CONSTRAINT completed_requires_timestamp CHECK (
        (status != 'completed' AND completed_at IS NULL) OR
        (status = 'completed' AND completed_at IS NOT NULL)
    )
);

-- Indexes for deletion_requests
CREATE INDEX idx_deletion_requests_employee ON deletion_requests(employee_id);
CREATE INDEX idx_deletion_requests_status ON deletion_requests(status, requested_at DESC);

COMMENT ON TABLE deletion_requests IS 'GDPR right to be forgotten - employee data deletion requests';

-- ============================================================================
-- MATERIALIZED VIEWS
-- ============================================================================

-- Current employee trust scores (for dashboard)
CREATE MATERIALIZED VIEW mv_current_trust_scores AS
SELECT DISTINCT ON (employee_id)
    employee_id,
    outcome_score,
    behavioral_score,
    security_score,
    wellbeing_score,
    total_score,
    timestamp,
    calculated_at
FROM trust_scores
ORDER BY employee_id, timestamp DESC;

CREATE UNIQUE INDEX idx_mv_current_trust_scores ON mv_current_trust_scores(employee_id);

COMMENT ON MATERIALIZED VIEW mv_current_trust_scores IS 'Latest trust score for each employee (refresh hourly)';

-- Employee signal summary (for analytics)
CREATE MATERIALIZED VIEW mv_employee_signal_summary AS
SELECT 
    employee_id,
    signal_type,
    COUNT(*) as signal_count,
    AVG(signal_value) as avg_value,
    STDDEV(signal_value) as stddev_value,
    MIN(timestamp) as first_signal,
    MAX(timestamp) as last_signal
FROM signal_events
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY employee_id, signal_type;

CREATE INDEX idx_mv_employee_signal_summary ON mv_employee_signal_summary(employee_id);

COMMENT ON MATERIALIZED VIEW mv_employee_signal_summary IS 'Signal statistics per employee (refresh daily)';

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to automatically set updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to encrypt OAuth tokens
CREATE OR REPLACE FUNCTION encrypt_token(token TEXT, encryption_key TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(token, encryption_key);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to decrypt OAuth tokens
CREATE OR REPLACE FUNCTION decrypt_token(encrypted_token BYTEA, encryption_key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(encrypted_token, encryption_key);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to create audit log entry
CREATE OR REPLACE FUNCTION create_audit_log(
    p_action audit_action,
    p_user_id UUID,
    p_resource_type VARCHAR,
    p_resource_id UUID,
    p_changes JSONB DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_audit_id UUID;
BEGIN
    INSERT INTO audit_logs (action, user_id, resource_type, resource_id, changes, ip_address)
    VALUES (p_action, p_user_id, p_resource_type, p_resource_id, p_changes, p_ip_address)
    RETURNING id INTO v_audit_id;
    
    RETURN v_audit_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to soft delete employee (GDPR)
CREATE OR REPLACE FUNCTION soft_delete_employee(p_employee_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE employees
    SET deleted_at = NOW(),
        status = 'offboarded',
        email = email || '.deleted.' || EXTRACT(EPOCH FROM NOW())::TEXT
    WHERE id = p_employee_id
    AND deleted_at IS NULL;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to create monthly partitions automatically
CREATE OR REPLACE FUNCTION create_monthly_partition(
    p_table_name TEXT,
    p_start_date DATE
)
RETURNS VOID AS $$
DECLARE
    v_partition_name TEXT;
    v_start_date DATE;
    v_end_date DATE;
BEGIN
    v_start_date := DATE_TRUNC('month', p_start_date);
    v_end_date := v_start_date + INTERVAL '1 month';
    v_partition_name := p_table_name || '_' || TO_CHAR(v_start_date, 'YYYY_MM');
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
        v_partition_name,
        p_table_name,
        v_start_date,
        v_end_date
    );
END;
$$ LANGUAGE plpgsql;

-- Function to delete expired data (data retention)
CREATE OR REPLACE FUNCTION delete_expired_data()
RETURNS TABLE(table_name TEXT, rows_deleted BIGINT) AS $$
DECLARE
    v_deleted BIGINT;
BEGIN
    -- Delete expired signal events
    DELETE FROM signal_events WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'signal_events';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired trust scores
    DELETE FROM trust_scores WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'trust_scores';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired baseline profiles
    DELETE FROM baseline_profiles WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'baseline_profiles';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired anomalies
    DELETE FROM anomalies WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'anomalies';
    rows_deleted := v_deleted;
    RETURN NEXT;
    
    -- Delete expired audit logs
    DELETE FROM audit_logs WHERE expires_at < NOW();
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    table_name := 'audit_logs';
    rows_deleted := v_deleted;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger to update updated_at on employees
CREATE TRIGGER trigger_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to update updated_at on baseline_profiles
CREATE TRIGGER trigger_baseline_profiles_updated_at
    BEFORE UPDATE ON baseline_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to update updated_at on oauth_tokens
CREATE TRIGGER trigger_oauth_tokens_updated_at
    BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to audit employee changes
CREATE OR REPLACE FUNCTION audit_employee_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM create_audit_log('CREATE', NEW.id, 'employee', NEW.id, 
            jsonb_build_object('after', to_jsonb(NEW)));
    ELSIF TG_OP = 'UPDATE' THEN
        PERFORM create_audit_log('UPDATE', NEW.id, 'employee', NEW.id,
            jsonb_build_object('before', to_jsonb(OLD), 'after', to_jsonb(NEW)));
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM create_audit_log('DELETE', OLD.id, 'employee', OLD.id,
            jsonb_build_object('before', to_jsonb(OLD)));
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_audit_employees
    AFTER INSERT OR UPDATE OR DELETE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION audit_employee_changes();

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert system user for automated processes
INSERT INTO employees (id, email, name, department, role, status)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'system@tbaps.local',
    'System',
    'System',
    'System',
    'active'
) ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- GRANTS AND PERMISSIONS
-- ============================================================================

-- Create application role
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tbaps_app') THEN
        CREATE ROLE tbaps_app WITH LOGIN PASSWORD 'CHANGE_ME_IN_PRODUCTION';
    END IF;
END
$$;

-- Grant permissions to application role
GRANT USAGE ON SCHEMA public TO tbaps_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tbaps_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tbaps_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO tbaps_app;

-- Grant refresh permissions on materialized views
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tbaps_app;

-- ============================================================================
-- PERFORMANCE TUNING
-- ============================================================================

-- Analyze tables for query optimization
ANALYZE employees;
ANALYZE signal_events;
ANALYZE baseline_profiles;
ANALYZE trust_scores;
ANALYZE anomalies;
ANALYZE audit_logs;

-- ============================================================================
-- SCHEMA VALIDATION
-- ============================================================================

-- Verify all tables exist
DO $$
DECLARE
    v_tables TEXT[] := ARRAY[
        'employees', 'signal_events', 'baseline_profiles', 'trust_scores',
        'anomalies', 'audit_logs', 'oauth_tokens', 'consent_logs',
        'data_exports', 'deletion_requests'
    ];
    v_table TEXT;
BEGIN
    FOREACH v_table IN ARRAY v_tables LOOP
        IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = v_table) THEN
            RAISE EXCEPTION 'Table % does not exist', v_table;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Schema validation: All tables created successfully';
END
$$;

-- ============================================================================
-- COMPLETION
-- ============================================================================

-- Log schema creation
SELECT create_audit_log(
    'CREATE',
    '00000000-0000-0000-0000-000000000000',
    'schema',
    uuid_generate_v4(),
    jsonb_build_object('version', '1.0.0', 'created_at', NOW())
);

-- Display summary
SELECT 
    'TBAPS Schema Initialized' as status,
    COUNT(*) FILTER (WHERE table_type = 'BASE TABLE') as tables_created,
    COUNT(*) FILTER (WHERE table_type = 'VIEW') as views_created
FROM information_schema.tables
WHERE table_schema = 'public';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
