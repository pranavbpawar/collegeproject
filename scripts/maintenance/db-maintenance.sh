#!/bin/bash
# ============================================================================
# TBAPS Database Maintenance Script
# ============================================================================
#
# DESCRIPTION:
#   Automated database maintenance for TBAPS PostgreSQL database
#   - Data retention enforcement
#   - Partition management
#   - Vacuum and analyze
#   - Materialized view refresh
#   - Statistics collection
#
# SCHEDULE:
#   Run daily at 3 AM via cron
#
# USAGE:
#   ./db-maintenance.sh [--dry-run] [--verbose]
#
# ============================================================================

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-tbaps_production}"
DB_USER="${DB_USER:-tbaps_user}"
LOG_FILE="/var/log/tbaps/maintenance/db-maintenance.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Flags
DRY_RUN=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
    fi
}

# Execute SQL
execute_sql() {
    local sql="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        info "DRY RUN: $description"
        info "SQL: $sql"
        return 0
    fi
    
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$sql" >> "$LOG_FILE" 2>&1; then
        log "✓ $description"
        return 0
    else
        error "✗ $description"
        return 1
    fi
}

# Start maintenance
log "========================================="
log "TBAPS Database Maintenance Started"
log "========================================="

if [ "$DRY_RUN" = true ]; then
    warning "Running in DRY RUN mode - no changes will be made"
fi

# ============================================================================
# 1. DATA RETENTION ENFORCEMENT
# ============================================================================

log ""
log "Step 1: Enforcing data retention policies..."

# Delete expired signal events (30 days)
RESULT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "DELETE FROM signal_events WHERE expires_at < NOW(); SELECT ROW_COUNT();" 2>&1 | tail -1 | tr -d ' ')

if [ -n "$RESULT" ] && [ "$RESULT" != "0" ]; then
    log "  Deleted $RESULT expired signal events"
else
    info "  No expired signal events to delete"
fi

# Delete expired trust scores (90 days)
RESULT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "DELETE FROM trust_scores WHERE expires_at < NOW(); SELECT ROW_COUNT();" 2>&1 | tail -1 | tr -d ' ')

if [ -n "$RESULT" ] && [ "$RESULT" != "0" ]; then
    log "  Deleted $RESULT expired trust scores"
else
    info "  No expired trust scores to delete"
fi

# Delete expired baseline profiles (90 days)
RESULT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "DELETE FROM baseline_profiles WHERE expires_at < NOW(); SELECT ROW_COUNT();" 2>&1 | tail -1 | tr -d ' ')

if [ -n "$RESULT" ] && [ "$RESULT" != "0" ]; then
    log "  Deleted $RESULT expired baseline profiles"
else
    info "  No expired baseline profiles to delete"
fi

# Delete expired anomalies (1 year)
RESULT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "DELETE FROM anomalies WHERE expires_at < NOW(); SELECT ROW_COUNT();" 2>&1 | tail -1 | tr -d ' ')

if [ -n "$RESULT" ] && [ "$RESULT" != "0" ]; then
    log "  Deleted $RESULT expired anomalies"
else
    info "  No expired anomalies to delete"
fi

# Delete expired audit logs (7 years)
RESULT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "DELETE FROM audit_logs WHERE expires_at < NOW(); SELECT ROW_COUNT();" 2>&1 | tail -1 | tr -d ' ')

if [ -n "$RESULT" ] && [ "$RESULT" != "0" ]; then
    log "  Deleted $RESULT expired audit logs"
else
    info "  No expired audit logs to delete"
fi

# ============================================================================
# 2. PARTITION MANAGEMENT
# ============================================================================

log ""
log "Step 2: Managing partitions..."

# Create partitions for next 3 months
for i in {0..2}; do
    MONTH_DATE=$(date -d "+$i months" +%Y-%m-01)
    
    execute_sql \
        "SELECT create_monthly_partition('signal_events', '$MONTH_DATE'::DATE);" \
        "Creating signal_events partition for $MONTH_DATE"
    
    execute_sql \
        "SELECT create_monthly_partition('trust_scores', '$MONTH_DATE'::DATE);" \
        "Creating trust_scores partition for $MONTH_DATE"
done

# Drop old partitions (older than 6 months)
OLD_DATE=$(date -d "-6 months" +%Y_%m)

for table in signal_events trust_scores; do
    PARTITIONS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE '${table}_%' AND tablename < '${table}_${OLD_DATE}';" 2>&1)
    
    if [ -n "$PARTITIONS" ]; then
        while IFS= read -r partition; do
            partition=$(echo "$partition" | tr -d ' ')
            if [ -n "$partition" ]; then
                execute_sql \
                    "DROP TABLE IF EXISTS $partition;" \
                    "Dropping old partition: $partition"
            fi
        done <<< "$PARTITIONS"
    else
        info "  No old partitions to drop for $table"
    fi
done

# ============================================================================
# 3. VACUUM AND ANALYZE
# ============================================================================

log ""
log "Step 3: Running VACUUM and ANALYZE..."

# Vacuum analyze all tables
TABLES=("employees" "signal_events" "baseline_profiles" "trust_scores" "anomalies" "audit_logs" "oauth_tokens" "consent_logs")

for table in "${TABLES[@]}"; do
    execute_sql \
        "VACUUM ANALYZE $table;" \
        "Vacuum analyzing $table"
done

# ============================================================================
# 4. REFRESH MATERIALIZED VIEWS
# ============================================================================

log ""
log "Step 4: Refreshing materialized views..."

execute_sql \
    "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_current_trust_scores;" \
    "Refreshing mv_current_trust_scores"

execute_sql \
    "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_employee_signal_summary;" \
    "Refreshing mv_employee_signal_summary"

# ============================================================================
# 5. UPDATE STATISTICS
# ============================================================================

log ""
log "Step 5: Updating table statistics..."

execute_sql \
    "ANALYZE;" \
    "Updating database statistics"

# ============================================================================
# 6. CHECK DATABASE SIZE
# ============================================================================

log ""
log "Step 6: Checking database size..."

DB_SIZE=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>&1 | tr -d ' ')

log "  Database size: $DB_SIZE"

# Check table sizes
log "  Top 5 largest tables:"
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT 
        schemaname || '.' || tablename AS table,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
    LIMIT 5;" 2>&1 | tee -a "$LOG_FILE"

# ============================================================================
# 7. CHECK FOR BLOAT
# ============================================================================

log ""
log "Step 7: Checking for table bloat..."

BLOAT_CHECK=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM pg_stat_user_tables WHERE n_dead_tup > 1000;" 2>&1 | tr -d ' ')

if [ "$BLOAT_CHECK" -gt 0 ]; then
    warning "  Found $BLOAT_CHECK tables with significant bloat"
    log "  Consider running VACUUM FULL on these tables during maintenance window"
else
    log "  No significant table bloat detected"
fi

# ============================================================================
# 8. CHECK LONG-RUNNING QUERIES
# ============================================================================

log ""
log "Step 8: Checking for long-running queries..."

LONG_QUERIES=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active' AND NOW() - query_start > INTERVAL '5 minutes';" 2>&1 | tr -d ' ')

if [ "$LONG_QUERIES" -gt 0 ]; then
    warning "  Found $LONG_QUERIES long-running queries (>5 minutes)"
else
    log "  No long-running queries detected"
fi

# ============================================================================
# 9. CHECK CONNECTION POOL
# ============================================================================

log ""
log "Step 9: Checking connection pool..."

CONNECTIONS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = '$DB_NAME';" 2>&1 | tr -d ' ')

MAX_CONNECTIONS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SHOW max_connections;" 2>&1 | tr -d ' ')

USAGE_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($CONNECTIONS/$MAX_CONNECTIONS)*100}")

log "  Active connections: $CONNECTIONS / $MAX_CONNECTIONS ($USAGE_PERCENT%)"

if (( $(echo "$USAGE_PERCENT > 80" | bc -l) )); then
    warning "  Connection pool usage is high (>80%)"
fi

# ============================================================================
# 10. LOG MAINTENANCE COMPLETION
# ============================================================================

log ""
log "Step 10: Logging maintenance completion..."

execute_sql \
    "INSERT INTO maintenance_log (task, status, details, completed_at, duration_seconds) 
     VALUES ('daily_maintenance', 'completed', '{\"dry_run\": $DRY_RUN}'::jsonb, NOW(), 
     EXTRACT(EPOCH FROM (NOW() - (SELECT started_at FROM maintenance_log ORDER BY started_at DESC LIMIT 1))));" \
    "Logging maintenance completion"

# ============================================================================
# SUMMARY
# ============================================================================

log ""
log "========================================="
log "TBAPS Database Maintenance Completed"
log "========================================="
log ""
log "Summary:"
log "  Database size: $DB_SIZE"
log "  Active connections: $CONNECTIONS / $MAX_CONNECTIONS"
log "  Long-running queries: $LONG_QUERIES"
log "  Tables with bloat: $BLOAT_CHECK"
log ""

if [ "$DRY_RUN" = true ]; then
    warning "DRY RUN mode - no changes were made"
fi

log "Maintenance log: $LOG_FILE"
log ""

exit 0
