-- ============================================================================
-- TBAPS GDPR Compliance Procedures
-- ============================================================================
--
-- DESCRIPTION:
--   SQL procedures for GDPR compliance including:
--   - Right to be forgotten (data deletion)
--   - Right to data portability (data export)
--   - Consent management
--   - Audit trail
--
-- COMPLIANCE:
--   - GDPR Article 17 (Right to erasure)
--   - GDPR Article 20 (Right to data portability)
--   - GDPR Article 30 (Records of processing activities)
--
-- ============================================================================

-- ============================================================================
-- PROCEDURE: Export Employee Data (GDPR Article 20)
-- ============================================================================

CREATE OR REPLACE FUNCTION export_employee_data(
    p_employee_id UUID,
    p_requested_by UUID DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_export_id UUID;
    v_export_data JSONB;
BEGIN
    -- Create export request
    INSERT INTO data_exports (
        employee_id,
        export_type,
        status,
        requested_by,
        ip_address,
        file_format
    ) VALUES (
        p_employee_id,
        'full_export',
        'processing',
        p_requested_by,
        p_ip_address,
        'json'
    ) RETURNING id INTO v_export_id;
    
    -- Build export data
    v_export_data := jsonb_build_object(
        'export_id', v_export_id,
        'export_date', NOW(),
        'employee', (
            SELECT to_jsonb(e) 
            FROM employees e 
            WHERE e.id = p_employee_id
        ),
        'signals', (
            SELECT jsonb_agg(to_jsonb(s))
            FROM signal_events s
            WHERE s.employee_id = p_employee_id
            AND s.timestamp > NOW() - INTERVAL '30 days'
        ),
        'trust_scores', (
            SELECT jsonb_agg(to_jsonb(t))
            FROM trust_scores t
            WHERE t.employee_id = p_employee_id
            AND t.timestamp > NOW() - INTERVAL '90 days'
        ),
        'baseline_profiles', (
            SELECT jsonb_agg(to_jsonb(b))
            FROM baseline_profiles b
            WHERE b.employee_id = p_employee_id
        ),
        'anomalies', (
            SELECT jsonb_agg(to_jsonb(a))
            FROM anomalies a
            WHERE a.employee_id = p_employee_id
        ),
        'consent_logs', (
            SELECT jsonb_agg(to_jsonb(c))
            FROM consent_logs c
            WHERE c.employee_id = p_employee_id
        ),
        'audit_trail', (
            SELECT jsonb_agg(to_jsonb(al))
            FROM audit_logs al
            WHERE al.user_id = p_employee_id
            ORDER BY al.timestamp DESC
            LIMIT 1000
        )
    );
    
    -- Update export request
    UPDATE data_exports
    SET 
        status = 'completed',
        completed_at = NOW(),
        file_size = length(v_export_data::text),
        expires_at = NOW() + INTERVAL '30 days'
    WHERE id = v_export_id;
    
    -- Create audit log
    PERFORM create_audit_log(
        'DATA_EXPORTED',
        COALESCE(p_requested_by, p_employee_id),
        'employee_data',
        p_employee_id,
        jsonb_build_object('export_id', v_export_id, 'size_bytes', length(v_export_data::text)),
        p_ip_address
    );
    
    RETURN v_export_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION export_employee_data IS 'GDPR Article 20: Export all employee data in portable format';

-- ============================================================================
-- PROCEDURE: Delete Employee Data (GDPR Article 17)
-- ============================================================================

CREATE OR REPLACE FUNCTION delete_employee_data(
    p_employee_id UUID,
    p_requested_by UUID,
    p_reason TEXT DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_deletion_id UUID;
    v_deletion_summary JSONB;
    v_signal_count BIGINT;
    v_score_count BIGINT;
    v_baseline_count BIGINT;
    v_anomaly_count BIGINT;
BEGIN
    -- Verify employee exists and is not already deleted
    IF NOT EXISTS (SELECT 1 FROM employees WHERE id = p_employee_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'Employee not found or already deleted';
    END IF;
    
    -- Create deletion request
    INSERT INTO deletion_requests (
        employee_id,
        status,
        reason,
        requested_by,
        ip_address
    ) VALUES (
        p_employee_id,
        'processing',
        p_reason,
        p_requested_by,
        p_ip_address
    ) RETURNING id INTO v_deletion_id;
    
    -- Count data to be deleted
    SELECT COUNT(*) INTO v_signal_count FROM signal_events WHERE employee_id = p_employee_id;
    SELECT COUNT(*) INTO v_score_count FROM trust_scores WHERE employee_id = p_employee_id;
    SELECT COUNT(*) INTO v_baseline_count FROM baseline_profiles WHERE employee_id = p_employee_id;
    SELECT COUNT(*) INTO v_anomaly_count FROM anomalies WHERE employee_id = p_employee_id;
    
    -- Delete signal events
    DELETE FROM signal_events WHERE employee_id = p_employee_id;
    
    -- Delete trust scores
    DELETE FROM trust_scores WHERE employee_id = p_employee_id;
    
    -- Delete baseline profiles
    DELETE FROM baseline_profiles WHERE employee_id = p_employee_id;
    
    -- Delete anomalies
    DELETE FROM anomalies WHERE employee_id = p_employee_id;
    
    -- Revoke OAuth tokens
    UPDATE oauth_tokens
    SET revoked = TRUE, revoked_at = NOW()
    WHERE employee_id = p_employee_id AND revoked = FALSE;
    
    -- Soft delete employee record
    PERFORM soft_delete_employee(p_employee_id);
    
    -- Build deletion summary
    v_deletion_summary := jsonb_build_object(
        'signals_deleted', v_signal_count,
        'scores_deleted', v_score_count,
        'baselines_deleted', v_baseline_count,
        'anomalies_deleted', v_anomaly_count,
        'oauth_tokens_revoked', (SELECT COUNT(*) FROM oauth_tokens WHERE employee_id = p_employee_id),
        'employee_soft_deleted', TRUE,
        'deletion_timestamp', NOW()
    );
    
    -- Update deletion request
    UPDATE deletion_requests
    SET 
        status = 'completed',
        completed_at = NOW(),
        deletion_summary = v_deletion_summary
    WHERE id = v_deletion_id;
    
    -- Create audit log
    PERFORM create_audit_log(
        'DATA_DELETED',
        p_requested_by,
        'employee_data',
        p_employee_id,
        jsonb_build_object('deletion_id', v_deletion_id, 'summary', v_deletion_summary),
        p_ip_address
    );
    
    RETURN v_deletion_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION delete_employee_data IS 'GDPR Article 17: Right to erasure (right to be forgotten)';

-- ============================================================================
-- PROCEDURE: Record Consent
-- ============================================================================

CREATE OR REPLACE FUNCTION record_consent(
    p_employee_id UUID,
    p_consent_type VARCHAR(50),
    p_consented BOOLEAN,
    p_consent_version VARCHAR(20),
    p_consent_text TEXT,
    p_ip_address INET
)
RETURNS UUID AS $$
DECLARE
    v_consent_id UUID;
BEGIN
    -- Insert consent log
    INSERT INTO consent_logs (
        employee_id,
        consent_type,
        consented,
        consent_version,
        consent_text,
        ip_address
    ) VALUES (
        p_employee_id,
        p_consent_type,
        p_consented,
        p_consent_version,
        p_consent_text,
        p_ip_address
    ) RETURNING id INTO v_consent_id;
    
    -- Create audit log
    PERFORM create_audit_log(
        CASE WHEN p_consented THEN 'CONSENT_GRANTED' ELSE 'CONSENT_WITHDRAWN' END,
        p_employee_id,
        'consent',
        v_consent_id,
        jsonb_build_object('consent_type', p_consent_type, 'version', p_consent_version),
        p_ip_address
    );
    
    RETURN v_consent_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION record_consent IS 'Record employee consent for GDPR compliance';

-- ============================================================================
-- PROCEDURE: Withdraw Consent
-- ============================================================================

CREATE OR REPLACE FUNCTION withdraw_consent(
    p_employee_id UUID,
    p_consent_type VARCHAR(50),
    p_ip_address INET DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_consent_id UUID;
BEGIN
    -- Find active consent
    SELECT id INTO v_consent_id
    FROM consent_logs
    WHERE employee_id = p_employee_id
    AND consent_type = p_consent_type
    AND consented = TRUE
    AND withdrawn_date IS NULL
    ORDER BY consent_date DESC
    LIMIT 1;
    
    IF v_consent_id IS NULL THEN
        RAISE EXCEPTION 'No active consent found for type: %', p_consent_type;
    END IF;
    
    -- Update consent log
    UPDATE consent_logs
    SET withdrawn_date = NOW()
    WHERE id = v_consent_id;
    
    -- Create audit log
    PERFORM create_audit_log(
        'CONSENT_WITHDRAWN',
        p_employee_id,
        'consent',
        v_consent_id,
        jsonb_build_object('consent_type', p_consent_type),
        p_ip_address
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION withdraw_consent IS 'Withdraw employee consent for GDPR compliance';

-- ============================================================================
-- PROCEDURE: Check Active Consents
-- ============================================================================

CREATE OR REPLACE FUNCTION check_active_consents(p_employee_id UUID)
RETURNS TABLE(
    consent_type VARCHAR(50),
    consented BOOLEAN,
    consent_date TIMESTAMP WITH TIME ZONE,
    consent_version VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (cl.consent_type)
        cl.consent_type,
        cl.consented,
        cl.consent_date,
        cl.consent_version
    FROM consent_logs cl
    WHERE cl.employee_id = p_employee_id
    AND cl.withdrawn_date IS NULL
    ORDER BY cl.consent_type, cl.consent_date DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION check_active_consents IS 'Check all active consents for an employee';

-- ============================================================================
-- PROCEDURE: Anonymize Employee Data (Alternative to Deletion)
-- ============================================================================

CREATE OR REPLACE FUNCTION anonymize_employee_data(
    p_employee_id UUID,
    p_requested_by UUID,
    p_ip_address INET DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_anonymous_id UUID;
BEGIN
    -- Generate anonymous ID
    v_anonymous_id := uuid_generate_v4();
    
    -- Anonymize employee record
    UPDATE employees
    SET 
        email = 'anonymous.' || v_anonymous_id || '@deleted.local',
        name = 'Anonymous User',
        department = NULL,
        role = NULL,
        manager_id = NULL,
        metadata = '{}',
        deleted_at = NOW(),
        status = 'offboarded'
    WHERE id = p_employee_id;
    
    -- Anonymize signal events (keep for statistical purposes)
    UPDATE signal_events
    SET metadata = metadata - 'email' - 'name' - 'user_agent'
    WHERE employee_id = p_employee_id;
    
    -- Create audit log
    PERFORM create_audit_log(
        'DATA_DELETED',
        p_requested_by,
        'employee_data',
        p_employee_id,
        jsonb_build_object('action', 'anonymized', 'anonymous_id', v_anonymous_id),
        p_ip_address
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION anonymize_employee_data IS 'Anonymize employee data while preserving statistical integrity';

-- ============================================================================
-- VIEW: GDPR Compliance Dashboard
-- ============================================================================

CREATE OR REPLACE VIEW v_gdpr_compliance AS
SELECT 
    'Total Employees' as metric,
    COUNT(*)::TEXT as value,
    'active' as category
FROM employees
WHERE deleted_at IS NULL AND status = 'active'

UNION ALL

SELECT 
    'Deleted Employees (Last 30 Days)',
    COUNT(*)::TEXT,
    'deletion'
FROM employees
WHERE deleted_at > NOW() - INTERVAL '30 days'

UNION ALL

SELECT 
    'Pending Deletion Requests',
    COUNT(*)::TEXT,
    'deletion'
FROM deletion_requests
WHERE status IN ('pending', 'approved', 'processing')

UNION ALL

SELECT 
    'Pending Export Requests',
    COUNT(*)::TEXT,
    'export'
FROM data_exports
WHERE status IN ('pending', 'processing')

UNION ALL

SELECT 
    'Active Consents',
    COUNT(DISTINCT employee_id)::TEXT,
    'consent'
FROM consent_logs
WHERE consented = TRUE AND withdrawn_date IS NULL

UNION ALL

SELECT 
    'Audit Log Entries (Last 30 Days)',
    COUNT(*)::TEXT,
    'audit'
FROM audit_logs
WHERE timestamp > NOW() - INTERVAL '30 days'

UNION ALL

SELECT 
    'Data Retention Compliance',
    CASE 
        WHEN COUNT(*) = 0 THEN 'Compliant'
        ELSE 'Non-Compliant (' || COUNT(*) || ' expired records)'
    END,
    'retention'
FROM (
    SELECT 1 FROM signal_events WHERE expires_at < NOW() LIMIT 1
    UNION ALL
    SELECT 1 FROM trust_scores WHERE expires_at < NOW() LIMIT 1
    UNION ALL
    SELECT 1 FROM baseline_profiles WHERE expires_at < NOW() LIMIT 1
) expired;

COMMENT ON VIEW v_gdpr_compliance IS 'GDPR compliance metrics dashboard';

-- ============================================================================
-- TEST PROCEDURES
-- ============================================================================

-- Test data export
DO $$
DECLARE
    v_test_employee_id UUID;
    v_export_id UUID;
BEGIN
    -- Get a test employee
    SELECT id INTO v_test_employee_id FROM employees WHERE email = 'system@tbaps.local';
    
    IF v_test_employee_id IS NOT NULL THEN
        -- Test export
        v_export_id := export_employee_data(v_test_employee_id, v_test_employee_id, '127.0.0.1'::INET);
        RAISE NOTICE 'Test export created: %', v_export_id;
    END IF;
END $$;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

/*

-- 1. Record employee consent
SELECT record_consent(
    'employee-uuid-here',
    'data_processing',
    TRUE,
    'v1.0',
    'I consent to my productivity data being processed...',
    '192.168.1.100'::INET
);

-- 2. Check active consents
SELECT * FROM check_active_consents('employee-uuid-here');

-- 3. Export employee data
SELECT export_employee_data(
    'employee-uuid-here',
    'admin-uuid-here',
    '192.168.1.100'::INET
);

-- 4. Delete employee data (GDPR right to be forgotten)
SELECT delete_employee_data(
    'employee-uuid-here',
    'admin-uuid-here',
    'Employee requested data deletion',
    '192.168.1.100'::INET
);

-- 5. Anonymize employee data (alternative to deletion)
SELECT anonymize_employee_data(
    'employee-uuid-here',
    'admin-uuid-here',
    '192.168.1.100'::INET
);

-- 6. View GDPR compliance status
SELECT * FROM v_gdpr_compliance;

-- 7. Withdraw consent
SELECT withdraw_consent(
    'employee-uuid-here',
    'email_analysis',
    '192.168.1.100'::INET
);

*/

-- ============================================================================
-- END OF GDPR PROCEDURES
-- ============================================================================

SELECT 'GDPR compliance procedures installed successfully' as status;
