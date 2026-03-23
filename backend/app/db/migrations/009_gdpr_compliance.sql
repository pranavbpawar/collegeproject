-- GDPR Compliance Tables
-- Audit logging and compliance tracking

-- ============================================================================
-- AUDIT LOGS (Immutable, 7-year retention)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    -- Primary identification
    id UUID PRIMARY KEY,
    employee_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    
    -- Action details
    action VARCHAR(50) NOT NULL,  -- GDPR action type
    performed_by VARCHAR(255) NOT NULL,  -- User who performed action
    ip_address VARCHAR(45),  -- IPv4 or IPv6
    
    -- Timestamp (immutable)
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Details
    resources_accessed TEXT,  -- JSON array of resources
    changes TEXT,  -- JSON object of changes
    
    -- Result
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    
    -- Constraints
    CONSTRAINT audit_logs_timestamp_check CHECK (timestamp <= NOW())
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_employee ON audit_logs(employee_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_performed_by ON audit_logs(performed_by);

-- Prevent updates and deletes (immutable)
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable and cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_prevent_audit_log_update
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();

CREATE TRIGGER trigger_prevent_audit_log_delete
    BEFORE DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();

-- Comments
COMMENT ON TABLE audit_logs IS 'Immutable audit trail for GDPR compliance (7-year retention)';
COMMENT ON COLUMN audit_logs.timestamp IS 'Immutable timestamp of action';


-- ============================================================================
-- GDPR REQUESTS TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS gdpr_requests (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Request details
    request_type VARCHAR(50) NOT NULL,  -- 'deletion', 'access', 'portability', 'rectification'
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    
    -- Requester
    requested_by VARCHAR(255) NOT NULL,
    request_reason TEXT,
    
    -- Dates
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    deadline TIMESTAMP WITH TIME ZONE,  -- 30-day deadline
    
    -- Results
    result_file TEXT,  -- Export file path
    records_affected INTEGER,
    tables_affected TEXT[],
    
    -- Audit
    audit_log_id UUID REFERENCES audit_logs(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_gdpr_requests_employee ON gdpr_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_gdpr_requests_status ON gdpr_requests(status);
CREATE INDEX IF NOT EXISTS idx_gdpr_requests_type ON gdpr_requests(request_type);
CREATE INDEX IF NOT EXISTS idx_gdpr_requests_deadline ON gdpr_requests(deadline) WHERE status = 'pending';

-- Auto-set deadline (30 days from request)
CREATE OR REPLACE FUNCTION set_gdpr_request_deadline()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.deadline IS NULL THEN
        NEW.deadline = NEW.requested_at + INTERVAL '30 days';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_gdpr_request_deadline
    BEFORE INSERT ON gdpr_requests
    FOR EACH ROW
    EXECUTE FUNCTION set_gdpr_request_deadline();

-- Comments
COMMENT ON TABLE gdpr_requests IS 'GDPR data subject requests tracking';
COMMENT ON COLUMN gdpr_requests.deadline IS 'Must respond within 30 days per GDPR';


-- ============================================================================
-- DATA RETENTION POLICIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS retention_policies (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Policy details
    table_name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,  -- Data category
    retention_days INTEGER NOT NULL,
    auto_delete BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,
    
    -- Last enforcement
    last_enforced_at TIMESTAMP WITH TIME ZONE,
    last_enforcement_deleted INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default policies
INSERT INTO retention_policies (table_name, category, retention_days, auto_delete, description) VALUES
    ('signal_events', 'work_activity', 90, TRUE, 'Work activity signals'),
    ('trust_scores', 'behavioral', 90, TRUE, 'Trust score history'),
    ('baseline_profiles', 'behavioral', 90, TRUE, 'Behavioral baselines'),
    ('anomalies', 'behavioral', 365, TRUE, 'Anomaly detections'),
    ('burnout_predictions', 'behavioral', 90, TRUE, 'Burnout predictions'),
    ('email_signals', 'work_activity', 90, TRUE, 'Email metadata signals'),
    ('oauth_tokens', 'technical', 365, TRUE, 'OAuth access tokens'),
    ('audit_logs', 'technical', 2555, FALSE, 'Audit trail (7-year retention)')
ON CONFLICT (table_name) DO NOTHING;

-- Comments
COMMENT ON TABLE retention_policies IS 'Data retention policies per GDPR Article 5';


-- ============================================================================
-- CONSENT TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS consent_records (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Consent details
    purpose VARCHAR(255) NOT NULL,  -- Purpose of data processing
    consent_given BOOLEAN NOT NULL,
    
    -- Metadata
    consent_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    withdrawn_date TIMESTAMP WITH TIME ZONE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    -- Audit
    audit_log_id UUID REFERENCES audit_logs(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_consent_records_employee ON consent_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_consent_records_purpose ON consent_records(purpose);
CREATE INDEX IF NOT EXISTS idx_consent_records_active 
    ON consent_records(employee_id, purpose) 
    WHERE consent_given = TRUE AND withdrawn_date IS NULL;

-- Comments
COMMENT ON TABLE consent_records IS 'Consent tracking per GDPR Article 7';


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get pending GDPR requests
CREATE OR REPLACE FUNCTION get_pending_gdpr_requests()
RETURNS TABLE (
    id UUID,
    employee_id UUID,
    request_type VARCHAR,
    requested_at TIMESTAMP WITH TIME ZONE,
    deadline TIMESTAMP WITH TIME ZONE,
    days_remaining INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        gr.id,
        gr.employee_id,
        gr.request_type,
        gr.requested_at,
        gr.deadline,
        EXTRACT(DAY FROM (gr.deadline - NOW()))::INTEGER as days_remaining
    FROM gdpr_requests gr
    WHERE gr.status = 'pending'
    ORDER BY gr.deadline ASC;
END;
$$ LANGUAGE plpgsql;


-- Get overdue GDPR requests
CREATE OR REPLACE FUNCTION get_overdue_gdpr_requests()
RETURNS TABLE (
    id UUID,
    employee_id UUID,
    request_type VARCHAR,
    requested_at TIMESTAMP WITH TIME ZONE,
    deadline TIMESTAMP WITH TIME ZONE,
    days_overdue INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        gr.id,
        gr.employee_id,
        gr.request_type,
        gr.requested_at,
        gr.deadline,
        EXTRACT(DAY FROM (NOW() - gr.deadline))::INTEGER as days_overdue
    FROM gdpr_requests gr
    WHERE gr.status = 'pending'
        AND gr.deadline < NOW()
    ORDER BY gr.deadline ASC;
END;
$$ LANGUAGE plpgsql;


-- Get audit trail for employee
CREATE OR REPLACE FUNCTION get_employee_audit_trail(
    p_employee_id UUID,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    id UUID,
    action VARCHAR,
    performed_by VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE,
    success BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        al.id,
        al.action,
        al.performed_by,
        al.timestamp,
        al.success
    FROM audit_logs al
    WHERE al.employee_id = p_employee_id
    ORDER BY al.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;


-- Check if data should be deleted per retention policy
CREATE OR REPLACE FUNCTION check_retention_compliance()
RETURNS TABLE (
    table_name VARCHAR,
    retention_days INTEGER,
    records_to_delete BIGINT,
    oldest_record TIMESTAMP WITH TIME ZONE
) AS $$
DECLARE
    policy RECORD;
    count_query TEXT;
    oldest_query TEXT;
    record_count BIGINT;
    oldest_ts TIMESTAMP WITH TIME ZONE;
BEGIN
    FOR policy IN SELECT * FROM retention_policies WHERE auto_delete = TRUE LOOP
        -- Build dynamic query to count records to delete
        count_query := format(
            'SELECT COUNT(*) FROM %I WHERE created_at < NOW() - INTERVAL ''%s days''',
            policy.table_name,
            policy.retention_days
        );
        
        -- Build dynamic query to find oldest record
        oldest_query := format(
            'SELECT MIN(created_at) FROM %I',
            policy.table_name
        );
        
        BEGIN
            EXECUTE count_query INTO record_count;
            EXECUTE oldest_query INTO oldest_ts;
            
            RETURN QUERY SELECT
                policy.table_name,
                policy.retention_days,
                record_count,
                oldest_ts;
        EXCEPTION WHEN OTHERS THEN
            -- Skip tables that don't exist or have errors
            CONTINUE;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Get pending requests
-- SELECT * FROM get_pending_gdpr_requests();

-- Get overdue requests
-- SELECT * FROM get_overdue_gdpr_requests();

-- Get audit trail
-- SELECT * FROM get_employee_audit_trail('emp_uuid', 100);

-- Check retention compliance
-- SELECT * FROM check_retention_compliance();
