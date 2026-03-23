# TBAPS Database Quick Reference

## 🚀 Quick Start

```bash
# 1. Initialize schema
psql -U tbaps_user -d tbaps_production -f scripts/init_schema.sql

# 2. Run migrations
psql -U tbaps_user -d tbaps_production -f scripts/migrations/001_initial_schema.sql

# 3. Install GDPR procedures
psql -U tbaps_user -d tbaps_production -f scripts/gdpr-procedures.sql

# 4. (Optional) Generate test data
psql -U tbaps_user -d tbaps_production -f scripts/generate-test-data.sql
```

## 📊 Tables at a Glance

| Table | Purpose | Retention | Partitioned |
|-------|---------|-----------|-------------|
| **employees** | Employee master data | Permanent | No |
| **signal_events** | Time-series signals | 30 days | Yes (monthly) |
| **baseline_profiles** | Behavioral baselines | 90 days | No |
| **trust_scores** | Historical scores | 90 days | Yes (monthly) |
| **anomalies** | Detected anomalies | 1 year | No |
| **audit_logs** | Audit trail | 7 years | No |
| **oauth_tokens** | Encrypted tokens | Until revoked | No |
| **consent_logs** | GDPR consents | Permanent | No |
| **data_exports** | Export requests | 30 days | No |
| **deletion_requests** | Deletion requests | Permanent | No |

## 🔧 Common Operations

### Insert Signal Event

```sql
INSERT INTO signal_events (
    employee_id, signal_type, signal_value, source, timestamp, expires_at
) VALUES (
    'employee-uuid',
    'email_sent',
    1.0,
    'office365',
    NOW(),
    NOW() + INTERVAL '30 days'
);
```

### Get Current Trust Score

```sql
SELECT * FROM mv_current_trust_scores 
WHERE employee_id = 'employee-uuid';
```

### Record Consent

```sql
SELECT record_consent(
    'employee-uuid',
    'data_processing',
    TRUE,
    'v1.0',
    'I consent to data processing...',
    '192.168.1.100'::INET
);
```

### Export Employee Data (GDPR)

```sql
SELECT export_employee_data(
    'employee-uuid',
    'admin-uuid',
    '192.168.1.100'::INET
);
```

### Delete Employee Data (GDPR)

```sql
SELECT delete_employee_data(
    'employee-uuid',
    'admin-uuid',
    'Employee requested deletion',
    '192.168.1.100'::INET
);
```

## 🔄 Maintenance

### Daily Maintenance (Automated)

```bash
# Run via cron at 3 AM
0 3 * * * /srv/tbaps/scripts/maintenance/db-maintenance.sh
```

### Manual Maintenance

```sql
-- Delete expired data
SELECT delete_expired_data();

-- Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_current_trust_scores;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_employee_signal_summary;

-- Update statistics
ANALYZE;

-- Vacuum tables
VACUUM ANALYZE employees;
```

### Create New Partition

```sql
-- Create partition for next month
SELECT create_monthly_partition('signal_events', '2026-03-01'::DATE);
SELECT create_monthly_partition('trust_scores', '2026-03-01'::DATE);
```

## 📈 Performance Queries

### Check Table Sizes

```sql
SELECT 
    schemaname || '.' || tablename AS table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Find Slow Queries

```sql
SELECT 
    query,
    calls,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Check Connection Pool

```sql
SELECT 
    COUNT(*) as active_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
FROM pg_stat_activity
WHERE datname = 'tbaps_production';
```

### Check for Bloat

```sql
SELECT 
    tablename,
    n_dead_tup,
    n_live_tup,
    round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

## 🔍 Useful Queries

### Get Signal Summary (Last 7 Days)

```sql
SELECT 
    signal_type,
    COUNT(*) as count,
    AVG(signal_value) as avg_value
FROM signal_events
WHERE employee_id = 'employee-uuid'
AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY signal_type;
```

### Get Unresolved Anomalies

```sql
SELECT 
    e.name,
    a.severity,
    a.description,
    a.flagged_at
FROM anomalies a
JOIN employees e ON a.employee_id = e.id
WHERE a.resolved = FALSE
ORDER BY a.severity DESC, a.flagged_at DESC;
```

### Department Analytics

```sql
SELECT 
    e.department,
    COUNT(DISTINCT e.id) as employee_count,
    AVG(t.total_score) as avg_trust_score
FROM employees e
LEFT JOIN mv_current_trust_scores t ON e.id = t.employee_id
WHERE e.deleted_at IS NULL
GROUP BY e.department
ORDER BY avg_trust_score DESC;
```

### Check Active Consents

```sql
SELECT * FROM check_active_consents('employee-uuid');
```

### GDPR Compliance Dashboard

```sql
SELECT * FROM v_gdpr_compliance;
```

## 🔐 Security

### Encrypt OAuth Token

```sql
SELECT encrypt_token('access_token_here', 'encryption_key');
```

### Decrypt OAuth Token

```sql
SELECT decrypt_token(encrypted_token, 'encryption_key');
```

### Create Audit Log

```sql
SELECT create_audit_log(
    'UPDATE',
    'user-uuid',
    'employee',
    'resource-uuid',
    '{"before": {...}, "after": {...}}'::jsonb,
    '192.168.1.100'::INET
);
```

## 📊 Monitoring

### Database Size

```sql
SELECT pg_size_pretty(pg_database_size('tbaps_production'));
```

### Active Queries

```sql
SELECT 
    pid,
    NOW() - query_start as duration,
    state,
    query
FROM pg_stat_activity
WHERE state = 'active'
AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;
```

### Index Usage

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## 🐛 Troubleshooting

### Kill Long-Running Query

```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE pid = 12345;
```

### Reset Statistics

```sql
SELECT pg_stat_reset();
```

### Check Locks

```sql
SELECT 
    l.locktype,
    l.relation::regclass,
    l.mode,
    l.granted,
    a.query
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE NOT l.granted;
```

## 📝 Backup & Restore

### Backup Database

```bash
pg_dump -U tbaps_user -d tbaps_production -F c -f tbaps_backup.dump
```

### Restore Database

```bash
pg_restore -U tbaps_user -d tbaps_production -c tbaps_backup.dump
```

### Backup Single Table

```bash
pg_dump -U tbaps_user -d tbaps_production -t employees -F c -f employees_backup.dump
```

## 🎯 Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Single employee lookup | < 10ms | Uses PK index |
| Trust score retrieval | < 50ms | Uses materialized view |
| Signal aggregation (7 days) | < 200ms | Uses partition pruning |
| Complex analytics | < 500ms | Uses multiple indexes |
| GDPR data export | < 5s | Full employee data |

## 📞 Support

- **Documentation:** `docs/database-architecture.md`
- **Scripts:** `scripts/`
- **Logs:** `/var/log/tbaps/postgres/`
- **Contact:** infrastructure@yourcompany.local

---

**Version:** 1.0.0  
**PostgreSQL:** 15+  
**Last Updated:** 2026-01-25
