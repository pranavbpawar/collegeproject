-- ============================================================================
-- TBAPS Database Test Data Generator
-- ============================================================================
--
-- DESCRIPTION:
--   Generate realistic test data for TBAPS database
--   - 100 employees
--   - 1M+ signal events (30 days)
--   - Baseline profiles
--   - Trust scores
--   - Anomalies
--
-- USAGE:
--   psql -U tbaps_user -d tbaps_production -f generate-test-data.sql
--
-- WARNING:
--   This will insert large amounts of test data.
--   Only run in development/testing environments!
--
-- ============================================================================

\echo 'Starting test data generation...'
\echo 'WARNING: This will insert large amounts of data!'
\echo ''

-- ============================================================================
-- 1. GENERATE EMPLOYEES
-- ============================================================================

\echo 'Step 1: Generating 100 test employees...'

INSERT INTO employees (email, name, department, role, status)
SELECT 
    'employee' || i || '@test.tbaps.local',
    'Test Employee ' || i,
    CASE (i % 5)
        WHEN 0 THEN 'Engineering'
        WHEN 1 THEN 'Sales'
        WHEN 2 THEN 'Marketing'
        WHEN 3 THEN 'Operations'
        ELSE 'Support'
    END,
    CASE (i % 4)
        WHEN 0 THEN 'Senior Engineer'
        WHEN 1 THEN 'Manager'
        WHEN 2 THEN 'Analyst'
        ELSE 'Specialist'
    END,
    'active'
FROM generate_series(1, 100) as i
ON CONFLICT (email) DO NOTHING;

\echo '  ✓ Created 100 employees'

-- ============================================================================
-- 2. GENERATE SIGNAL EVENTS (1M records over 30 days)
-- ============================================================================

\echo 'Step 2: Generating 1M signal events (this may take a few minutes)...'

-- Generate signals in batches
DO $$
DECLARE
    v_employee_id UUID;
    v_batch_size INTEGER := 10000;
    v_total_signals INTEGER := 1000000;
    v_batches INTEGER := v_total_signals / v_batch_size;
    v_batch INTEGER;
BEGIN
    FOR v_batch IN 1..v_batches LOOP
        INSERT INTO signal_events (
            employee_id,
            signal_type,
            signal_value,
            metadata,
            source,
            timestamp,
            expires_at
        )
        SELECT 
            (SELECT id FROM employees WHERE deleted_at IS NULL ORDER BY RANDOM() LIMIT 1),
            (ARRAY['calendar_event', 'email_sent', 'email_received', 'task_created', 'task_completed', 'meeting_attended'])[floor(random() * 6 + 1)]::signal_type,
            random() * 100,
            jsonb_build_object(
                'duration_minutes', floor(random() * 120),
                'participants', floor(random() * 10),
                'priority', (ARRAY['low', 'medium', 'high'])[floor(random() * 3 + 1)]
            ),
            (ARRAY['google_calendar', 'office365', 'jira', 'asana'])[floor(random() * 4 + 1)],
            NOW() - (random() * INTERVAL '30 days'),
            NOW() + INTERVAL '30 days'
        FROM generate_series(1, v_batch_size);
        
        IF v_batch % 10 = 0 THEN
            RAISE NOTICE 'Generated % / % signals (% complete)', 
                v_batch * v_batch_size, 
                v_total_signals,
                round((v_batch::NUMERIC / v_batches) * 100, 1);
        END IF;
    END LOOP;
END $$;

\echo '  ✓ Created 1M signal events'

-- ============================================================================
-- 3. GENERATE BASELINE PROFILES
-- ============================================================================

\echo 'Step 3: Generating baseline profiles...'

INSERT INTO baseline_profiles (
    employee_id,
    metric,
    baseline_value,
    std_dev,
    p95,
    p50,
    p05,
    min_value,
    max_value,
    confidence,
    sample_size,
    calculation_start,
    calculation_end,
    expires_at
)
SELECT 
    e.id,
    metric,
    50 + random() * 50,  -- baseline_value
    5 + random() * 10,   -- std_dev
    80 + random() * 20,  -- p95
    50 + random() * 20,  -- p50
    10 + random() * 20,  -- p05
    5 + random() * 10,   -- min
    90 + random() * 10,  -- max
    0.7 + random() * 0.3, -- confidence
    floor(random() * 1000 + 100)::INTEGER, -- sample_size
    NOW() - INTERVAL '30 days',
    NOW(),
    NOW() + INTERVAL '90 days'
FROM employees e
CROSS JOIN (
    VALUES 
        ('meetings_per_day'),
        ('email_response_time_minutes'),
        ('tasks_completed_per_day'),
        ('average_meeting_duration_minutes'),
        ('code_commits_per_day'),
        ('documents_created_per_day')
) AS metrics(metric)
WHERE e.deleted_at IS NULL;

\echo '  ✓ Created baseline profiles'

-- ============================================================================
-- 4. GENERATE TRUST SCORES
-- ============================================================================

\echo 'Step 4: Generating trust scores (90 days)...'

INSERT INTO trust_scores (
    employee_id,
    outcome_score,
    behavioral_score,
    security_score,
    wellbeing_score,
    total_score,
    timestamp,
    expires_at
)
SELECT 
    e.id,
    60 + random() * 40,  -- outcome_score
    60 + random() * 40,  -- behavioral_score
    70 + random() * 30,  -- security_score
    65 + random() * 35,  -- wellbeing_score
    65 + random() * 30,  -- total_score
    NOW() - (i || ' days')::INTERVAL,
    NOW() + INTERVAL '90 days'
FROM employees e
CROSS JOIN generate_series(0, 89) as i
WHERE e.deleted_at IS NULL;

\echo '  ✓ Created trust scores'

-- ============================================================================
-- 5. GENERATE ANOMALIES
-- ============================================================================

\echo 'Step 5: Generating anomalies...'

INSERT INTO anomalies (
    employee_id,
    anomaly_type,
    severity,
    description,
    signals_involved,
    baseline_deviation,
    resolved,
    flagged_at,
    expires_at
)
SELECT 
    e.id,
    (ARRAY['statistical', 'rule_based', 'ml_predicted'])[floor(random() * 3 + 1)]::anomaly_type,
    (ARRAY['low', 'medium', 'high'])[floor(random() * 3 + 1)]::anomaly_severity,
    'Detected unusual pattern in ' || 
        (ARRAY['meeting attendance', 'email response time', 'task completion rate'])[floor(random() * 3 + 1)],
    '[]'::jsonb,
    2.5 + random() * 2.5,  -- 2.5-5 std devs
    random() > 0.3,  -- 70% resolved
    NOW() - (random() * INTERVAL '365 days'),
    NOW() + INTERVAL '1 year'
FROM employees e
CROSS JOIN generate_series(1, 3) as i  -- 3 anomalies per employee
WHERE e.deleted_at IS NULL
AND random() > 0.5;  -- Only 50% of employees have anomalies

\echo '  ✓ Created anomalies'

-- ============================================================================
-- 6. GENERATE CONSENT LOGS
-- ============================================================================

\echo 'Step 6: Generating consent logs...'

INSERT INTO consent_logs (
    employee_id,
    consent_type,
    consented,
    consent_version,
    consent_text,
    ip_address
)
SELECT 
    e.id,
    consent_type,
    TRUE,
    'v1.0',
    'I consent to ' || consent_type || ' for productivity monitoring purposes.',
    ('192.168.1.' || floor(random() * 254 + 1))::INET
FROM employees e
CROSS JOIN (
    VALUES 
        ('data_processing'),
        ('monitoring'),
        ('email_analysis'),
        ('calendar_analysis')
) AS consents(consent_type)
WHERE e.deleted_at IS NULL;

\echo '  ✓ Created consent logs'

-- ============================================================================
-- 7. GENERATE OAUTH TOKENS
-- ============================================================================

\echo 'Step 7: Generating OAuth tokens...'

INSERT INTO oauth_tokens (
    employee_id,
    service,
    encrypted_token,
    encrypted_refresh_token,
    expires_at
)
SELECT 
    e.id,
    service,
    pgp_sym_encrypt('test_token_' || e.id || '_' || service, 'test_encryption_key'),
    pgp_sym_encrypt('test_refresh_' || e.id || '_' || service, 'test_encryption_key'),
    NOW() + INTERVAL '1 hour'
FROM employees e
CROSS JOIN (
    VALUES 
        ('google_calendar'),
        ('office365')
) AS services(service)
WHERE e.deleted_at IS NULL
AND random() > 0.3;  -- 70% of employees have OAuth tokens

\echo '  ✓ Created OAuth tokens'

-- ============================================================================
-- 8. REFRESH MATERIALIZED VIEWS
-- ============================================================================

\echo 'Step 8: Refreshing materialized views...'

REFRESH MATERIALIZED VIEW mv_current_trust_scores;
REFRESH MATERIALIZED VIEW mv_employee_signal_summary;

\echo '  ✓ Refreshed materialized views'

-- ============================================================================
-- 9. UPDATE STATISTICS
-- ============================================================================

\echo 'Step 9: Updating database statistics...'

ANALYZE employees;
ANALYZE signal_events;
ANALYZE baseline_profiles;
ANALYZE trust_scores;
ANALYZE anomalies;
ANALYZE consent_logs;
ANALYZE oauth_tokens;

\echo '  ✓ Updated statistics'

-- ============================================================================
-- SUMMARY
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'Test Data Generation Complete!'
\echo '========================================='
\echo ''

-- Display summary
SELECT 
    'employees' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('employees')) as table_size
FROM employees
WHERE deleted_at IS NULL

UNION ALL

SELECT 
    'signal_events',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('signal_events'))
FROM signal_events

UNION ALL

SELECT 
    'baseline_profiles',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('baseline_profiles'))
FROM baseline_profiles

UNION ALL

SELECT 
    'trust_scores',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('trust_scores'))
FROM trust_scores

UNION ALL

SELECT 
    'anomalies',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('anomalies'))
FROM anomalies

UNION ALL

SELECT 
    'consent_logs',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('consent_logs'))
FROM consent_logs

UNION ALL

SELECT 
    'oauth_tokens',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('oauth_tokens'))
FROM oauth_tokens;

\echo ''
\echo 'Database ready for testing!'
\echo ''

-- ============================================================================
-- PERFORMANCE TEST QUERIES
-- ============================================================================

\echo 'Running performance test queries...'
\echo ''

-- Test 1: Get employee trust scores
\timing on

\echo 'Test 1: Get employee trust scores (should be < 100ms)'
SELECT e.name, t.total_score, t.timestamp
FROM employees e
JOIN mv_current_trust_scores t ON e.id = t.employee_id
WHERE e.deleted_at IS NULL
ORDER BY t.total_score DESC
LIMIT 10;

-- Test 2: Get signal summary for employee
\echo 'Test 2: Get signal summary for employee (should be < 200ms)'
SELECT 
    signal_type,
    COUNT(*) as count,
    AVG(signal_value) as avg_value
FROM signal_events
WHERE employee_id = (SELECT id FROM employees WHERE deleted_at IS NULL LIMIT 1)
AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY signal_type;

-- Test 3: Get anomalies
\echo 'Test 3: Get unresolved anomalies (should be < 100ms)'
SELECT 
    e.name,
    a.severity,
    a.description,
    a.flagged_at
FROM anomalies a
JOIN employees e ON a.employee_id = e.id
WHERE a.resolved = FALSE
ORDER BY a.flagged_at DESC
LIMIT 20;

-- Test 4: Complex join query
\echo 'Test 4: Complex analytics query (should be < 500ms)'
SELECT 
    e.department,
    COUNT(DISTINCT e.id) as employee_count,
    AVG(t.total_score) as avg_trust_score,
    COUNT(a.id) as anomaly_count
FROM employees e
LEFT JOIN mv_current_trust_scores t ON e.id = t.employee_id
LEFT JOIN anomalies a ON e.id = a.employee_id AND a.resolved = FALSE
WHERE e.deleted_at IS NULL
GROUP BY e.department
ORDER BY avg_trust_score DESC;

\timing off

\echo ''
\echo 'Performance tests complete!'
\echo ''

-- ============================================================================
-- END OF TEST DATA GENERATION
-- ============================================================================
