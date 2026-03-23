-- Anomaly Detection Tables
-- Stores detected anomalies from 3-tier detection system

CREATE TABLE IF NOT EXISTS anomalies (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Detection results
    is_anomaly BOOLEAN NOT NULL,
    votes INTEGER NOT NULL,  -- Number of tiers that detected anomaly (0-3)
    confidence DECIMAL(5, 4) NOT NULL,  -- 0.0 to 1.0
    severity VARCHAR(20) NOT NULL,  -- 'low', 'medium', 'high', 'critical'
    
    -- Tier results
    statistical_detected BOOLEAN DEFAULT FALSE,
    statistical_confidence DECIMAL(5, 4),
    statistical_z_score DECIMAL(10, 4),
    
    rule_based_detected BOOLEAN DEFAULT FALSE,
    rule_based_confidence DECIMAL(5, 4),
    triggered_rules JSONB,  -- Array of triggered rule names
    
    ml_detected BOOLEAN DEFAULT FALSE,
    ml_confidence DECIMAL(5, 4),
    ml_anomaly_score DECIMAL(10, 6),
    
    -- Anomaly details
    anomaly_types TEXT[],  -- Array of anomaly type names
    signal_data JSONB,  -- Original signal data
    baseline_data JSONB,  -- Baseline used for detection
    
    -- Metadata
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Investigation
    investigated BOOLEAN DEFAULT FALSE,
    investigated_by UUID REFERENCES employees(id),
    investigated_at TIMESTAMP WITH TIME ZONE,
    investigation_notes TEXT,
    false_positive BOOLEAN,
    
    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_anomalies_employee ON anomalies(employee_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON anomalies(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_is_anomaly ON anomalies(is_anomaly);
CREATE INDEX IF NOT EXISTS idx_anomalies_unresolved ON anomalies(resolved) WHERE resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_anomalies_uninvestigated ON anomalies(investigated) WHERE investigated = FALSE;

-- Composite indexes
CREATE INDEX IF NOT EXISTS idx_anomalies_employee_detected 
    ON anomalies(employee_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity_unresolved 
    ON anomalies(severity, resolved) WHERE resolved = FALSE;

-- GIN index for JSONB
CREATE INDEX IF NOT EXISTS idx_anomalies_triggered_rules ON anomalies USING GIN (triggered_rules);
CREATE INDEX IF NOT EXISTS idx_anomalies_signal_data ON anomalies USING GIN (signal_data);

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_anomalies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_anomalies_updated_at
    BEFORE UPDATE ON anomalies
    FOR EACH ROW
    EXECUTE FUNCTION update_anomalies_updated_at();

-- Comments
COMMENT ON TABLE anomalies IS 'Detected anomalies from 3-tier detection system';
COMMENT ON COLUMN anomalies.votes IS 'Number of detection tiers that flagged as anomaly (0-3)';
COMMENT ON COLUMN anomalies.triggered_rules IS 'JSON array of triggered security rules';
COMMENT ON COLUMN anomalies.anomaly_types IS 'Array of anomaly type identifiers';


-- ============================================================================
-- ANOMALY STATISTICS VIEW
-- ============================================================================

CREATE OR REPLACE VIEW anomaly_statistics AS
SELECT
    employee_id,
    COUNT(*) as total_anomalies,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) as confirmed_anomalies,
    SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical_count,
    SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high_count,
    SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium_count,
    SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low_count,
    SUM(CASE WHEN statistical_detected THEN 1 ELSE 0 END) as statistical_detections,
    SUM(CASE WHEN rule_based_detected THEN 1 ELSE 0 END) as rule_detections,
    SUM(CASE WHEN ml_detected THEN 1 ELSE 0 END) as ml_detections,
    AVG(votes) as avg_votes,
    AVG(confidence) as avg_confidence,
    SUM(CASE WHEN investigated THEN 1 ELSE 0 END) as investigated_count,
    SUM(CASE WHEN false_positive THEN 1 ELSE 0 END) as false_positive_count,
    SUM(CASE WHEN resolved THEN 1 ELSE 0 END) as resolved_count,
    MIN(detected_at) as first_anomaly,
    MAX(detected_at) as last_anomaly
FROM anomalies
GROUP BY employee_id;

COMMENT ON VIEW anomaly_statistics IS 'Aggregated anomaly statistics per employee';


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get recent anomalies for employee
CREATE OR REPLACE FUNCTION get_employee_anomalies(
    p_employee_id UUID,
    p_days INTEGER DEFAULT 30,
    p_severity VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    is_anomaly BOOLEAN,
    votes INTEGER,
    confidence DECIMAL,
    severity VARCHAR,
    anomaly_types TEXT[],
    detected_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.is_anomaly,
        a.votes,
        a.confidence,
        a.severity,
        a.anomaly_types,
        a.detected_at
    FROM anomalies a
    WHERE a.employee_id = p_employee_id
        AND a.detected_at > NOW() - (p_days || ' days')::INTERVAL
        AND (p_severity IS NULL OR a.severity = p_severity)
    ORDER BY a.detected_at DESC;
END;
$$ LANGUAGE plpgsql;


-- Calculate anomaly rate for employee
CREATE OR REPLACE FUNCTION calculate_anomaly_rate(
    p_employee_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS DECIMAL AS $$
DECLARE
    v_total_checks INTEGER;
    v_anomaly_count INTEGER;
BEGIN
    -- Count total anomaly checks
    SELECT COUNT(*)
    INTO v_total_checks
    FROM anomalies
    WHERE employee_id = p_employee_id
        AND detected_at > NOW() - (p_days || ' days')::INTERVAL;
    
    -- Count confirmed anomalies
    SELECT COUNT(*)
    INTO v_anomaly_count
    FROM anomalies
    WHERE employee_id = p_employee_id
        AND detected_at > NOW() - (p_days || ' days')::INTERVAL
        AND is_anomaly = TRUE;
    
    -- Calculate rate
    IF v_total_checks = 0 THEN
        RETURN 0.0;
    END IF;
    
    RETURN v_anomaly_count::DECIMAL / v_total_checks;
END;
$$ LANGUAGE plpgsql;


-- Get unresolved critical anomalies
CREATE OR REPLACE FUNCTION get_critical_unresolved_anomalies()
RETURNS TABLE (
    employee_id UUID,
    anomaly_count BIGINT,
    latest_anomaly TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.employee_id,
        COUNT(*) as anomaly_count,
        MAX(a.detected_at) as latest_anomaly
    FROM anomalies a
    WHERE a.severity = 'critical'
        AND a.resolved = FALSE
        AND a.detected_at > NOW() - INTERVAL '7 days'
    GROUP BY a.employee_id
    HAVING COUNT(*) > 0
    ORDER BY COUNT(*) DESC, MAX(a.detected_at) DESC;
END;
$$ LANGUAGE plpgsql;


-- Calculate false positive rate
CREATE OR REPLACE FUNCTION calculate_false_positive_rate(
    p_days INTEGER DEFAULT 30
)
RETURNS DECIMAL AS $$
DECLARE
    v_investigated INTEGER;
    v_false_positives INTEGER;
BEGIN
    -- Count investigated anomalies
    SELECT COUNT(*)
    INTO v_investigated
    FROM anomalies
    WHERE investigated = TRUE
        AND detected_at > NOW() - (p_days || ' days')::INTERVAL;
    
    -- Count false positives
    SELECT COUNT(*)
    INTO v_false_positives
    FROM anomalies
    WHERE investigated = TRUE
        AND false_positive = TRUE
        AND detected_at > NOW() - (p_days || ' days')::INTERVAL;
    
    -- Calculate rate
    IF v_investigated = 0 THEN
        RETURN 0.0;
    END IF;
    
    RETURN v_false_positives::DECIMAL / v_investigated;
END;
$$ LANGUAGE plpgsql;


-- Calculate true positive rate (detection accuracy)
CREATE OR REPLACE FUNCTION calculate_detection_accuracy(
    p_days INTEGER DEFAULT 30
)
RETURNS DECIMAL AS $$
DECLARE
    v_investigated INTEGER;
    v_true_positives INTEGER;
BEGIN
    -- Count investigated anomalies
    SELECT COUNT(*)
    INTO v_investigated
    FROM anomalies
    WHERE investigated = TRUE
        AND detected_at > NOW() - (p_days || ' days')::INTERVAL;
    
    -- Count true positives (not false positives)
    SELECT COUNT(*)
    INTO v_true_positives
    FROM anomalies
    WHERE investigated = TRUE
        AND (false_positive = FALSE OR false_positive IS NULL)
        AND detected_at > NOW() - (p_days || ' days')::INTERVAL;
    
    -- Calculate accuracy
    IF v_investigated = 0 THEN
        RETURN 0.0;
    END IF;
    
    RETURN v_true_positives::DECIMAL / v_investigated;
END;
$$ LANGUAGE plpgsql;


-- Get tier performance metrics
CREATE OR REPLACE FUNCTION get_tier_performance()
RETURNS TABLE (
    tier VARCHAR,
    total_detections BIGINT,
    avg_confidence DECIMAL,
    false_positive_rate DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    -- Statistical tier
    SELECT
        'statistical'::VARCHAR as tier,
        COUNT(*) as total_detections,
        AVG(statistical_confidence) as avg_confidence,
        SUM(CASE WHEN false_positive THEN 1 ELSE 0 END)::DECIMAL / 
            NULLIF(SUM(CASE WHEN investigated THEN 1 ELSE 0 END), 0) as false_positive_rate
    FROM anomalies
    WHERE statistical_detected = TRUE
    
    UNION ALL
    
    -- Rule-based tier
    SELECT
        'rule_based'::VARCHAR as tier,
        COUNT(*) as total_detections,
        AVG(rule_based_confidence) as avg_confidence,
        SUM(CASE WHEN false_positive THEN 1 ELSE 0 END)::DECIMAL / 
            NULLIF(SUM(CASE WHEN investigated THEN 1 ELSE 0 END), 0) as false_positive_rate
    FROM anomalies
    WHERE rule_based_detected = TRUE
    
    UNION ALL
    
    -- ML tier
    SELECT
        'machine_learning'::VARCHAR as tier,
        COUNT(*) as total_detections,
        AVG(ml_confidence) as avg_confidence,
        SUM(CASE WHEN false_positive THEN 1 ELSE 0 END)::DECIMAL / 
            NULLIF(SUM(CASE WHEN investigated THEN 1 ELSE 0 END), 0) as false_positive_rate
    FROM anomalies
    WHERE ml_detected = TRUE;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Get all unresolved critical anomalies
-- SELECT * FROM anomalies
-- WHERE severity = 'critical' AND resolved = FALSE
-- ORDER BY detected_at DESC;

-- Get anomaly statistics for employee
-- SELECT * FROM anomaly_statistics
-- WHERE employee_id = 'emp_uuid';

-- Get false positive rate
-- SELECT calculate_false_positive_rate(30);

-- Get detection accuracy
-- SELECT calculate_detection_accuracy(30);

-- Get tier performance
-- SELECT * FROM get_tier_performance();
