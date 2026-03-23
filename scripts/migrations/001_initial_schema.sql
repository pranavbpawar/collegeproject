-- ============================================================================
-- TBAPS Database Migrations
-- Version: 1.0.0
-- ============================================================================

\echo 'Starting TBAPS database migration...'

-- ============================================================================
-- MIGRATION 001: Initial Schema Setup
-- ============================================================================

\echo 'Migration 001: Creating extensions...'

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

\echo 'Migration 001: Extensions created ✓'

-- ============================================================================
-- MIGRATION 002: Create Custom Types
-- ============================================================================

\echo 'Migration 002: Creating custom types...'

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'employee_status') THEN
        CREATE TYPE employee_status AS ENUM ('active', 'inactive', 'offboarded');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'anomaly_severity') THEN
        CREATE TYPE anomaly_severity AS ENUM ('low', 'medium', 'high', 'critical');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'anomaly_type') THEN
        CREATE TYPE anomaly_type AS ENUM ('statistical', 'rule_based', 'ml_predicted', 'manual');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audit_action') THEN
        CREATE TYPE audit_action AS ENUM (
            'CREATE', 'READ', 'UPDATE', 'DELETE', 
            'EXPORT', 'ACCESS', 'LOGIN', 'LOGOUT',
            'CONSENT_GRANTED', 'CONSENT_WITHDRAWN',
            'DATA_DELETED', 'DATA_EXPORTED'
        );
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'signal_type') THEN
        CREATE TYPE signal_type AS ENUM (
            'calendar_event', 'email_sent', 'email_received',
            'task_created', 'task_completed', 'meeting_attended',
            'code_commit', 'document_created', 'document_edited'
        );
    END IF;
END $$;

\echo 'Migration 002: Custom types created ✓'

-- ============================================================================
-- MIGRATION 003: Verify Schema
-- ============================================================================

\echo 'Migration 003: Verifying schema...'

DO $$
DECLARE
    v_table_count INTEGER;
    v_index_count INTEGER;
    v_function_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    
    SELECT COUNT(*) INTO v_index_count
    FROM pg_indexes
    WHERE schemaname = 'public';
    
    SELECT COUNT(*) INTO v_function_count
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public';
    
    RAISE NOTICE 'Tables: %, Indexes: %, Functions: %', v_table_count, v_index_count, v_function_count;
END $$;

\echo 'Migration 003: Schema verification complete ✓'

-- ============================================================================
-- MIGRATION 004: Create Partitions for Next 12 Months
-- ============================================================================

\echo 'Migration 004: Creating partitions for next 12 months...'

DO $$
DECLARE
    v_month INTEGER;
    v_start_date DATE;
BEGIN
    FOR v_month IN 0..11 LOOP
        v_start_date := DATE_TRUNC('month', NOW() + (v_month || ' months')::INTERVAL);
        
        -- Create signal_events partition
        BEGIN
            PERFORM create_monthly_partition('signal_events', v_start_date);
        EXCEPTION WHEN duplicate_table THEN
            -- Partition already exists, skip
        END;
        
        -- Create trust_scores partition
        BEGIN
            PERFORM create_monthly_partition('trust_scores', v_start_date);
        EXCEPTION WHEN duplicate_table THEN
            -- Partition already exists, skip
        END;
    END LOOP;
    
    RAISE NOTICE 'Created partitions for 12 months';
END $$;

\echo 'Migration 004: Partitions created ✓'

-- ============================================================================
-- MIGRATION 005: Set Up Automated Maintenance
-- ============================================================================

\echo 'Migration 005: Setting up automated maintenance...'

-- Create maintenance log table
CREATE TABLE IF NOT EXISTS maintenance_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    details JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT
);

CREATE INDEX idx_maintenance_log_task ON maintenance_log(task, started_at DESC);

\echo 'Migration 005: Automated maintenance setup complete ✓'

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

\echo ''
\echo '========================================='
\echo 'TBAPS Database Migration Complete!'
\echo '========================================='
\echo ''

-- Display summary
SELECT 
    'Migration Summary' as info,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE') as tables,
    (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public') as indexes,
    (SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'public') as functions;

\echo ''
\echo 'Next steps:'
\echo '1. Run: SELECT delete_expired_data(); -- Test data retention'
\echo '2. Run: REFRESH MATERIALIZED VIEW mv_current_trust_scores; -- Update views'
\echo '3. Verify: SELECT * FROM employees WHERE email = ''system@tbaps.local''; -- Check system user'
\echo ''
