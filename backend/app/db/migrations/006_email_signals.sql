-- Email Signals Table
-- Stores extracted email intelligence signals (GDPR compliant - NO email body content)

CREATE TABLE IF NOT EXISTS email_signals (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id VARCHAR(255) UNIQUE NOT NULL,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    
    -- Response time metrics
    response_time_minutes DECIMAL(10, 2),
    response_time_score DECIMAL(5, 2),  -- 0-100 score
    
    -- Sentiment analysis (from subject line only)
    sentiment_compound DECIMAL(5, 4),  -- -1 to 1
    sentiment_positive DECIMAL(5, 4),  -- 0 to 1
    sentiment_negative DECIMAL(5, 4),  -- 0 to 1
    sentiment_neutral DECIMAL(5, 4),   -- 0 to 1
    sentiment_label VARCHAR(20),       -- 'positive', 'negative', 'neutral'
    
    -- Urgency detection
    is_urgent BOOLEAN DEFAULT FALSE,
    urgency_score DECIMAL(5, 4),  -- 0 to 1
    
    -- Communication metrics
    recipient_count INTEGER DEFAULT 1,
    subject_word_count INTEGER DEFAULT 0,
    communication_pattern VARCHAR(50),  -- 'quick_responder', 'slow_responder', etc.
    
    -- Metadata
    sent_at TIMESTAMP WITH TIME ZONE,
    is_business_hours BOOLEAN,
    day_of_week INTEGER,  -- 0=Monday, 6=Sunday
    hour_of_day INTEGER,  -- 0-23
    
    -- Timestamps
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_signals_employee ON email_signals(employee_id);
CREATE INDEX IF NOT EXISTS idx_email_signals_extracted_at ON email_signals(extracted_at);
CREATE INDEX IF NOT EXISTS idx_email_signals_is_urgent ON email_signals(is_urgent);
CREATE INDEX IF NOT EXISTS idx_email_signals_sentiment ON email_signals(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_email_signals_pattern ON email_signals(communication_pattern);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_email_signals_employee_extracted 
    ON email_signals(employee_id, extracted_at DESC);

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_email_signals_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_email_signals_updated_at
    BEFORE UPDATE ON email_signals
    FOR EACH ROW
    EXECUTE FUNCTION update_email_signals_updated_at();

-- Comments for documentation
COMMENT ON TABLE email_signals IS 'Email intelligence signals extracted from metadata only (GDPR compliant - NO email body content stored)';
COMMENT ON COLUMN email_signals.email_id IS 'External email identifier (from Gmail, Outlook, etc.)';
COMMENT ON COLUMN email_signals.sentiment_compound IS 'VADER compound sentiment score (-1 to 1)';
COMMENT ON COLUMN email_signals.urgency_score IS 'Urgency detection score (0 to 1)';
COMMENT ON COLUMN email_signals.communication_pattern IS 'Detected communication pattern (quick_responder, slow_responder, broadcaster, urgent_communicator, normal)';


-- ============================================================================
-- EMAIL STATISTICS VIEW
-- ============================================================================

CREATE OR REPLACE VIEW email_statistics AS
SELECT
    employee_id,
    COUNT(*) as total_emails,
    AVG(response_time_minutes) as avg_response_time,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time_minutes) as median_response_time,
    AVG(sentiment_compound) as avg_sentiment,
    SUM(CASE WHEN is_urgent THEN 1 ELSE 0 END) as urgent_count,
    SUM(CASE WHEN is_urgent THEN 1 ELSE 0 END)::DECIMAL / NULLIF(COUNT(*), 0) as urgent_rate,
    AVG(recipient_count) as avg_recipients,
    AVG(subject_word_count) as avg_subject_length,
    MODE() WITHIN GROUP (ORDER BY communication_pattern) as primary_pattern,
    SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
    SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
    MIN(extracted_at) as first_analyzed,
    MAX(extracted_at) as last_analyzed
FROM email_signals
GROUP BY employee_id;

COMMENT ON VIEW email_statistics IS 'Aggregated email statistics per employee';


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get email signals for employee in date range
CREATE OR REPLACE FUNCTION get_employee_email_signals(
    p_employee_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    email_id VARCHAR,
    response_time_minutes DECIMAL,
    sentiment_label VARCHAR,
    is_urgent BOOLEAN,
    communication_pattern VARCHAR,
    extracted_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        es.email_id,
        es.response_time_minutes,
        es.sentiment_label,
        es.is_urgent,
        es.communication_pattern,
        es.extracted_at
    FROM email_signals es
    WHERE es.employee_id = p_employee_id
        AND es.extracted_at > NOW() - (p_days || ' days')::INTERVAL
    ORDER BY es.extracted_at DESC;
END;
$$ LANGUAGE plpgsql;


-- Calculate email-based trust component
CREATE OR REPLACE FUNCTION calculate_email_trust_component(
    p_employee_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS DECIMAL AS $$
DECLARE
    v_response_score DECIMAL;
    v_sentiment_score DECIMAL;
    v_urgency_penalty DECIMAL;
    v_final_score DECIMAL;
BEGIN
    -- Calculate response time score (0-100)
    SELECT
        CASE
            WHEN AVG(response_time_minutes) < 30 THEN 100
            WHEN AVG(response_time_minutes) < 60 THEN 90
            WHEN AVG(response_time_minutes) < 120 THEN 80
            WHEN AVG(response_time_minutes) < 240 THEN 70
            WHEN AVG(response_time_minutes) < 480 THEN 60
            ELSE 50
        END
    INTO v_response_score
    FROM email_signals
    WHERE employee_id = p_employee_id
        AND extracted_at > NOW() - (p_days || ' days')::INTERVAL
        AND response_time_minutes IS NOT NULL;
    
    -- Calculate sentiment score (0-100)
    SELECT
        ((AVG(sentiment_compound) + 1) / 2) * 100
    INTO v_sentiment_score
    FROM email_signals
    WHERE employee_id = p_employee_id
        AND extracted_at > NOW() - (p_days || ' days')::INTERVAL;
    
    -- Calculate urgency penalty (excessive urgent emails = lower score)
    SELECT
        CASE
            WHEN (SUM(CASE WHEN is_urgent THEN 1 ELSE 0 END)::DECIMAL / NULLIF(COUNT(*), 0)) > 0.5 THEN 10
            WHEN (SUM(CASE WHEN is_urgent THEN 1 ELSE 0 END)::DECIMAL / NULLIF(COUNT(*), 0)) > 0.3 THEN 5
            ELSE 0
        END
    INTO v_urgency_penalty
    FROM email_signals
    WHERE employee_id = p_employee_id
        AND extracted_at > NOW() - (p_days || ' days')::INTERVAL;
    
    -- Combine scores (60% response time, 40% sentiment, minus urgency penalty)
    v_final_score := (
        COALESCE(v_response_score, 75) * 0.6 +
        COALESCE(v_sentiment_score, 50) * 0.4 -
        COALESCE(v_urgency_penalty, 0)
    );
    
    -- Ensure score is between 0 and 100
    RETURN GREATEST(0, LEAST(100, v_final_score));
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_email_trust_component IS 'Calculate trust score component based on email signals (0-100)';


-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Get employees with slow response times
-- SELECT employee_id, avg_response_time
-- FROM email_statistics
-- WHERE avg_response_time > 240
-- ORDER BY avg_response_time DESC;

-- Get employees with high urgency rates
-- SELECT employee_id, urgent_rate, urgent_count
-- FROM email_statistics
-- WHERE urgent_rate > 0.3
-- ORDER BY urgent_rate DESC;

-- Get employees with negative sentiment
-- SELECT employee_id, avg_sentiment, negative_count
-- FROM email_statistics
-- WHERE avg_sentiment < -0.1
-- ORDER BY avg_sentiment ASC;
