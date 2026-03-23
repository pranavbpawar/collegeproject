-- Burnout Predictions Table
-- Stores burnout risk predictions and recommendations

CREATE TABLE IF NOT EXISTS burnout_predictions (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Prediction results
    burnout_score DECIMAL(5, 2) NOT NULL,  -- 0-100
    risk_level VARCHAR(20) NOT NULL,  -- 'low', 'moderate', 'high', 'critical'
    confidence DECIMAL(5, 4) NOT NULL,  -- 0-1
    
    -- Indicator scores
    excessive_hours BOOLEAN NOT NULL,
    excessive_hours_score DECIMAL(5, 2),
    
    low_engagement BOOLEAN NOT NULL,
    engagement_score DECIMAL(5, 2),
    
    productivity_decline BOOLEAN NOT NULL,
    productivity_score DECIMAL(5, 2),
    
    sleep_issues BOOLEAN NOT NULL,
    sleep_score DECIMAL(5, 2),
    
    high_stress BOOLEAN NOT NULL,
    stress_score DECIMAL(5, 2),
    
    -- Recommendations
    recommendations JSONB,  -- Array of recommendation objects
    
    -- Dates
    prediction_date TIMESTAMP WITH TIME ZONE NOT NULL,  -- 4 weeks ahead
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Intervention tracking
    intervention_taken BOOLEAN DEFAULT FALSE,
    intervention_type VARCHAR(100),
    intervention_date TIMESTAMP WITH TIME ZONE,
    intervention_notes TEXT,
    
    -- Outcome tracking
    outcome_verified BOOLEAN DEFAULT FALSE,
    actual_burnout BOOLEAN,
    verification_date TIMESTAMP WITH TIME ZONE,
    verification_notes TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_burnout_predictions_employee ON burnout_predictions(employee_id);
CREATE INDEX IF NOT EXISTS idx_burnout_predictions_calculated ON burnout_predictions(calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_burnout_predictions_risk ON burnout_predictions(risk_level);
CREATE INDEX IF NOT EXISTS idx_burnout_predictions_prediction_date ON burnout_predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_burnout_predictions_high_risk 
    ON burnout_predictions(risk_level, employee_id) 
    WHERE risk_level IN ('high', 'critical');

-- Composite indexes
CREATE INDEX IF NOT EXISTS idx_burnout_predictions_employee_calculated 
    ON burnout_predictions(employee_id, calculated_at DESC);

-- GIN index for recommendations
CREATE INDEX IF NOT EXISTS idx_burnout_predictions_recommendations 
    ON burnout_predictions USING GIN (recommendations);

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_burnout_predictions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_burnout_predictions_updated_at
    BEFORE UPDATE ON burnout_predictions
    FOR EACH ROW
    EXECUTE FUNCTION update_burnout_predictions_updated_at();

-- Comments
COMMENT ON TABLE burnout_predictions IS 'Burnout risk predictions with 4-week advance warning';
COMMENT ON COLUMN burnout_predictions.burnout_score IS 'Overall burnout risk score (0-100)';
COMMENT ON COLUMN burnout_predictions.prediction_date IS 'Date of predicted burnout (4 weeks from calculation)';
COMMENT ON COLUMN burnout_predictions.recommendations IS 'JSON array of actionable recommendations';


-- ============================================================================
-- BURNOUT STATISTICS VIEW
-- ============================================================================

CREATE OR REPLACE VIEW burnout_statistics AS
SELECT
    employee_id,
    COUNT(*) as total_predictions,
    AVG(burnout_score) as avg_burnout_score,
    MAX(burnout_score) as max_burnout_score,
    SUM(CASE WHEN risk_level = 'critical' THEN 1 ELSE 0 END) as critical_count,
    SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as high_count,
    SUM(CASE WHEN risk_level = 'moderate' THEN 1 ELSE 0 END) as moderate_count,
    SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END) as low_count,
    SUM(CASE WHEN excessive_hours THEN 1 ELSE 0 END) as excessive_hours_count,
    SUM(CASE WHEN low_engagement THEN 1 ELSE 0 END) as low_engagement_count,
    SUM(CASE WHEN productivity_decline THEN 1 ELSE 0 END) as productivity_decline_count,
    SUM(CASE WHEN sleep_issues THEN 1 ELSE 0 END) as sleep_issues_count,
    SUM(CASE WHEN high_stress THEN 1 ELSE 0 END) as high_stress_count,
    SUM(CASE WHEN intervention_taken THEN 1 ELSE 0 END) as interventions_taken,
    AVG(confidence) as avg_confidence,
    MIN(calculated_at) as first_prediction,
    MAX(calculated_at) as last_prediction
FROM burnout_predictions
GROUP BY employee_id;

COMMENT ON VIEW burnout_statistics IS 'Aggregated burnout prediction statistics per employee';


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get latest prediction for employee
CREATE OR REPLACE FUNCTION get_latest_burnout_prediction(
    p_employee_id UUID
)
RETURNS TABLE (
    burnout_score DECIMAL,
    risk_level VARCHAR,
    confidence DECIMAL,
    prediction_date TIMESTAMP WITH TIME ZONE,
    recommendations JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        bp.burnout_score,
        bp.risk_level,
        bp.confidence,
        bp.prediction_date,
        bp.recommendations
    FROM burnout_predictions bp
    WHERE bp.employee_id = p_employee_id
    ORDER BY bp.calculated_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;


-- Get employees at high burnout risk
CREATE OR REPLACE FUNCTION get_high_risk_employees()
RETURNS TABLE (
    employee_id UUID,
    burnout_score DECIMAL,
    risk_level VARCHAR,
    prediction_date TIMESTAMP WITH TIME ZONE,
    intervention_taken BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (bp.employee_id)
        bp.employee_id,
        bp.burnout_score,
        bp.risk_level,
        bp.prediction_date,
        bp.intervention_taken
    FROM burnout_predictions bp
    WHERE bp.risk_level IN ('high', 'critical')
        AND bp.prediction_date > NOW()
        AND bp.calculated_at > NOW() - INTERVAL '7 days'
    ORDER BY bp.employee_id, bp.calculated_at DESC;
END;
$$ LANGUAGE plpgsql;


-- Calculate prediction accuracy
CREATE OR REPLACE FUNCTION calculate_burnout_prediction_accuracy()
RETURNS DECIMAL AS $$
DECLARE
    v_verified INTEGER;
    v_correct INTEGER;
BEGIN
    -- Count verified predictions
    SELECT COUNT(*)
    INTO v_verified
    FROM burnout_predictions
    WHERE outcome_verified = TRUE;
    
    -- Count correct predictions
    -- High/Critical risk + actual burnout = correct
    -- Low/Moderate risk + no burnout = correct
    SELECT COUNT(*)
    INTO v_correct
    FROM burnout_predictions
    WHERE outcome_verified = TRUE
        AND (
            (risk_level IN ('high', 'critical') AND actual_burnout = TRUE)
            OR
            (risk_level IN ('low', 'moderate') AND actual_burnout = FALSE)
        );
    
    -- Calculate accuracy
    IF v_verified = 0 THEN
        RETURN 0.0;
    END IF;
    
    RETURN v_correct::DECIMAL / v_verified;
END;
$$ LANGUAGE plpgsql;


-- Get indicator trends for employee
CREATE OR REPLACE FUNCTION get_indicator_trends(
    p_employee_id UUID,
    p_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    calculated_at TIMESTAMP WITH TIME ZONE,
    excessive_hours_score DECIMAL,
    engagement_score DECIMAL,
    productivity_score DECIMAL,
    sleep_score DECIMAL,
    stress_score DECIMAL,
    burnout_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        bp.calculated_at,
        bp.excessive_hours_score,
        bp.engagement_score,
        bp.productivity_score,
        bp.sleep_score,
        bp.stress_score,
        bp.burnout_score
    FROM burnout_predictions bp
    WHERE bp.employee_id = p_employee_id
        AND bp.calculated_at > NOW() - (p_days || ' days')::INTERVAL
    ORDER BY bp.calculated_at ASC;
END;
$$ LANGUAGE plpgsql;


-- Get intervention effectiveness
CREATE OR REPLACE FUNCTION get_intervention_effectiveness()
RETURNS TABLE (
    intervention_type VARCHAR,
    total_interventions BIGINT,
    successful_interventions BIGINT,
    effectiveness_rate DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        bp.intervention_type,
        COUNT(*) as total_interventions,
        SUM(CASE WHEN bp.actual_burnout = FALSE THEN 1 ELSE 0 END) as successful_interventions,
        SUM(CASE WHEN bp.actual_burnout = FALSE THEN 1 ELSE 0 END)::DECIMAL / 
            NULLIF(COUNT(*), 0) as effectiveness_rate
    FROM burnout_predictions bp
    WHERE bp.intervention_taken = TRUE
        AND bp.outcome_verified = TRUE
    GROUP BY bp.intervention_type;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Get latest prediction for employee
-- SELECT * FROM get_latest_burnout_prediction('emp_uuid');

-- Get all high-risk employees
-- SELECT * FROM get_high_risk_employees();

-- Get prediction accuracy
-- SELECT calculate_burnout_prediction_accuracy();

-- Get indicator trends
-- SELECT * FROM get_indicator_trends('emp_uuid', 90);

-- Get intervention effectiveness
-- SELECT * FROM get_intervention_effectiveness();
