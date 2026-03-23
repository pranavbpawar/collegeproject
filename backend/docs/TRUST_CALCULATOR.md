# TBAPS Trust Score Calculator

## Overview

The Trust Score Calculator is a comprehensive scoring engine that calculates daily trust scores for all employees by combining four weighted components with time-decay factors for recent events.

## Trust Score Formula

```
Total Trust Score = (
  Outcome × 0.35 +
  Behavioral × 0.30 +
  Security × 0.20 +
  Wellbeing × 0.15
) × Time Decay Factor
```

**Range:** 0-100 (higher is better)

---

## Component Breakdown

### 1. Outcome Reliability (35%)

Measures task completion, quality, and deadline adherence.

**Sub-components:**
- **Task Completion Rate (40%):** Percentage of tasks completed
- **Quality Score (35%):** `1 - (defects/tasks completed)`
- **Deadline Adherence (25%):** Percentage of tasks completed on time

**Formula:**
```
Outcome = (completion × 0.40 + quality × 0.35 + deadline × 0.25) × 100
```

**Data Sources:**
- Task created/completed signals from Jira, Asana
- Metadata: `task_id`, `on_time`, `has_defects`

**Interpretation:**
- **90-100:** Exceptional performance, high quality, always on time
- **70-89:** Good performance, occasional delays or minor issues
- **50-69:** Average performance, some quality concerns
- **Below 50:** Poor performance, frequent delays or quality issues

---

### 2. Behavioral Consistency (30%)

Measures pattern stability, response times, and collaboration.

**Sub-components:**
- **Pattern Deviation (40%):** Z-score of daily patterns vs baseline
- **Response Time Consistency (35%):** How close to baseline response times
- **Collaboration Score (25%):** Meeting attendance and participation

**Formula:**
```
Behavioral = ((1 - deviation) × 0.40 + response × 0.35 + collab × 0.25) × 100
```

**Data Sources:**
- Email signals (response times)
- Meeting attendance signals
- Baseline profiles for comparison

**Interpretation:**
- **90-100:** Highly consistent, reliable patterns
- **70-89:** Generally consistent with minor variations
- **50-69:** Some inconsistency, occasional pattern changes
- **Below 50:** Highly inconsistent, unpredictable patterns

---

### 3. Security Hygiene (20%)

Measures security compliance and safe practices.

**Sub-components:**
- **MFA Enabled (33%):** Multi-factor authentication status
- **VPN Compliance (33%):** Percentage of time VPN is used for sensitive data
- **Phishing Safety (34%):** `1 - (phishing incidents/emails)`

**Formula:**
```
Security = (mfa × 0.33 + vpn × 0.33 + phishing × 0.34) × 100
```

**Data Sources:**
- Security signals with metadata: `mfa_enabled`, `vpn_connected`, `sensitive_data_access`
- Email signals with `phishing_detected`, `clicked_phishing`

**Interpretation:**
- **90-100:** Excellent security practices, fully compliant
- **70-89:** Good security, minor compliance gaps
- **50-69:** Moderate security, needs improvement
- **Below 50:** Poor security practices, high risk

---

### 4. Psychological Wellbeing (15%)

Measures engagement, stress levels, and sentiment.

**Sub-components:**
- **Engagement Score (35%):** Work quality and enthusiasm signals
- **Stress Level (40%):** `1 - (stress indicators/total hours)`
- **Sentiment Score (25%):** Email sentiment analysis

**Formula:**
```
Wellbeing = (engagement × 0.35 + (1-stress) × 0.40 + sentiment × 0.25) × 100
```

**Data Sources:**
- Productive signals: code commits, documents, tasks
- Work hour patterns (long days, odd hours, weekends)
- Email sentiment metadata

**Interpretation:**
- **90-100:** Highly engaged, low stress, positive sentiment
- **70-89:** Good wellbeing, manageable stress
- **50-69:** Moderate concerns, elevated stress
- **Below 50:** Burnout risk, high stress, negative sentiment

---

## Time Decay

Recent events are weighted more heavily than older events:

| Age Range | Weight | Description |
|-----------|--------|-------------|
| 0-7 days | 100% | Recent data, full weight |
| 8-14 days | 80% | Week-old data, slightly reduced |
| 15-30 days | 60% | Month-old data, reduced weight |
| 30+ days | 0% | Ignored, too old |

**Formula:**
```python
decay_factor = weighted_sum / total_signals
```

---

## Usage

### CLI Commands

```bash
# Calculate scores for all employees
python3 scripts/trust_calculator_cli.py calculate-all

# Calculate score for specific employee
python3 scripts/trust_calculator_cli.py calculate-employee --employee-id abc-123-def

# Get latest score for employee
python3 scripts/trust_calculator_cli.py get-score --employee-id abc-123-def

# List top 20 employees by total score
python3 scripts/trust_calculator_cli.py list-scores --limit 20 --sort-by total

# List top employees by security score
python3 scripts/trust_calculator_cli.py list-scores --sort-by security
```

### Python API

```python
from app.services.trust_calculator import TrustCalculator

# Initialize calculator
calculator = TrustCalculator(window_days=30)

# Calculate all employees
summary = await calculator.calculate_daily_scores()

# Calculate single employee
score = await calculator.calculate_trust_score(employee_id)

# Access component scores
print(f"Total: {score['total']}")
print(f"Outcome: {score['outcome']}")
print(f"Behavioral: {score['behavioral']}")
print(f"Security: {score['security']}")
print(f"Wellbeing: {score['wellbeing']}")
print(f"Time Decay: {score['time_decay_factor']}")
```

---

## Cron Schedule

The trust calculator runs automatically on the following schedule:

```
# Daily calculation at 6:00 AM
0 6 * * * - Calculate all employee scores

# Weekly full recalculation on Sunday at 7:00 AM
0 7 * * 0 - Full 30-day window recalculation

# Hourly check for new employees
0 * * * * - Quick calculation for new employees
```

**Installation:**
```bash
sudo cp backend/scripts/trust_calculator.cron /etc/cron.d/tbaps-trust-calculator
sudo chmod 644 /etc/cron.d/tbaps-trust-calculator
sudo systemctl restart cron
```

---

## Database Schema

### trust_scores Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `employee_id` | UUID | Foreign key to employees |
| `outcome_score` | FLOAT | Outcome reliability score (0-100) |
| `behavioral_score` | FLOAT | Behavioral consistency score (0-100) |
| `security_score` | FLOAT | Security hygiene score (0-100) |
| `wellbeing_score` | FLOAT | Psychological wellbeing score (0-100) |
| `total_score` | FLOAT | Combined trust score (0-100) |
| `weights` | JSONB | Component weights used |
| `timestamp` | TIMESTAMP | Score timestamp |
| `calculated_at` | TIMESTAMP | Calculation time |
| `expires_at` | TIMESTAMP | Expiration time (30 days) |

**Partitioning:** Monthly partitions by `timestamp`

**Indexes:**
- `employee_id` (for lookups)
- `timestamp` (for time-based queries)
- `total_score` (for rankings)

---

## Performance

### Calculation Speed

- **Per Employee:** < 1 second
- **100 Employees:** < 2 minutes
- **1000 Employees:** < 15 minutes

### Optimization Tips

1. **Database Indexes:** Ensure indexes on `signal_events.employee_id` and `signal_events.timestamp`
2. **Baseline Availability:** Pre-calculate baselines for faster comparison
3. **Batch Processing:** Process employees in batches of 100
4. **Caching:** Cache baseline profiles during calculation run

---

## Validation

### Weight Validation

All component weights must sum to 1.0:

```python
assert sum(WEIGHTS.values()) == 1.0
assert sum(OUTCOME_WEIGHTS.values()) == 1.0
assert sum(BEHAVIORAL_WEIGHTS.values()) == 1.0
assert sum(SECURITY_WEIGHTS.values()) == 1.0
assert sum(WELLBEING_WEIGHTS.values()) == 1.0
```

### Score Validation

All scores must be in the 0-100 range:

```python
assert 0 <= score['total'] <= 100
assert 0 <= score['outcome'] <= 100
assert 0 <= score['behavioral'] <= 100
assert 0 <= score['security'] <= 100
assert 0 <= score['wellbeing'] <= 100
```

### Time Decay Validation

Time decay factor must be between 0 and 1:

```python
assert 0 <= time_decay_factor <= 1.0
```

---

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest backend/tests/test_trust_calculator.py -v

# Run specific test
pytest backend/tests/test_trust_calculator.py::test_weights_sum_to_one -v

# Run with coverage
pytest backend/tests/test_trust_calculator.py --cov=app.services.trust_calculator
```

### Test Coverage

- ✅ Component weight validation
- ✅ Time decay calculation
- ✅ Outcome score calculation
- ✅ Behavioral score calculation
- ✅ Security score calculation
- ✅ Wellbeing score calculation
- ✅ Score normalization
- ✅ Edge cases (no data, perfect scores)

---

## Troubleshooting

### No Scores Calculated

**Symptoms:** `calculate_daily_scores()` returns 0 successful calculations

**Causes:**
1. No signal data in database
2. No baseline profiles established
3. Employees marked as inactive

**Solutions:**
```bash
# Check signal data
psql -d tbaps -c "SELECT COUNT(*) FROM signal_events;"

# Check baselines
psql -d tbaps -c "SELECT COUNT(*) FROM baseline_profiles;"

# Check active employees
psql -d tbaps -c "SELECT COUNT(*) FROM employees WHERE status='active';"

# Establish baselines first
python3 scripts/baseline_cli.py establish-all
```

### Low Scores Across Board

**Symptoms:** All employees have low trust scores

**Causes:**
1. Insufficient signal data
2. Poor data quality (missing metadata)
3. Incorrect baseline values

**Solutions:**
1. Verify integrations are syncing properly
2. Check signal metadata completeness
3. Recalculate baselines with more data

### Calculation Takes Too Long

**Symptoms:** Calculation takes > 5 seconds per employee

**Causes:**
1. Missing database indexes
2. Too many signals (> 1000 per employee)
3. Slow baseline queries

**Solutions:**
```sql
-- Add indexes
CREATE INDEX IF NOT EXISTS idx_signal_events_employee_timestamp 
ON signal_events(employee_id, timestamp);

-- Partition signal_events table
-- Limit signal retention to 90 days
```

---

## Logging

### Log Files

- **Main Log:** `/var/log/tbaps/trust_calculator.log`
- **Cron Log:** `/var/log/tbaps/trust_calculator_cron.log`

### Log Levels

```python
# DEBUG: Detailed calculation steps
logger.debug(f"Calculated score for {employee_id}: {score}")

# INFO: High-level progress
logger.info(f"Processing {total_employees} active employees")

# WARNING: Non-critical issues
logger.warning(f"Insufficient data for {employee_id}")

# ERROR: Critical failures
logger.error(f"Database error during calculation: {e}")
```

### View Logs

```bash
# Tail main log
tail -f /var/log/tbaps/trust_calculator.log

# View cron log
tail -f /var/log/tbaps/trust_calculator_cron.log

# Search for errors
grep ERROR /var/log/tbaps/trust_calculator.log

# View specific employee
grep "employee_id" /var/log/tbaps/trust_calculator.log
```

---

## API Integration

### FastAPI Endpoints

```python
# Get employee trust score
GET /api/v1/trust-scores/{employee_id}

# List all trust scores
GET /api/v1/trust-scores?limit=100&sort_by=total

# Get trust score history
GET /api/v1/trust-scores/{employee_id}/history?days=30

# Trigger recalculation
POST /api/v1/trust-scores/calculate
```

### Response Format

```json
{
  "employee_id": "abc-123-def",
  "total_score": 85.5,
  "outcome_score": 88.2,
  "behavioral_score": 82.1,
  "security_score": 90.0,
  "wellbeing_score": 78.5,
  "time_decay_factor": 0.95,
  "timestamp": "2026-01-25T06:00:00Z",
  "calculated_at": "2026-01-25T06:05:23Z"
}
```

---

## Best Practices

### 1. Run Daily

Calculate scores daily at the same time (6 AM recommended) to maintain consistency.

### 2. Monitor Trends

Track score changes over time to identify patterns:
- Sudden drops may indicate issues
- Gradual declines may indicate burnout
- Improvements show positive changes

### 3. Combine with Baselines

Use trust scores alongside baseline profiles for comprehensive analysis:
- Trust score shows current state
- Baseline shows normal patterns
- Deviation shows anomalies

### 4. Set Thresholds

Define organizational thresholds for action:
- **< 50:** Immediate intervention required
- **50-70:** Monitor closely, offer support
- **70-85:** Normal range, no action needed
- **85-100:** High performers, recognize achievements

### 5. Privacy Considerations

Trust scores are sensitive data:
- Limit access to HR and management
- Use for support, not punishment
- Combine with human judgment
- Respect employee privacy

---

## Files

| File | Purpose |
|------|---------|
| `app/services/trust_calculator.py` | Main calculator engine |
| `scripts/trust_calculator_cli.py` | CLI tool |
| `scripts/trust_calculator.cron` | Cron configuration |
| `tests/test_trust_calculator.py` | Unit tests |
| `docs/TRUST_CALCULATOR.md` | This documentation |

---

## Version History

**Version 1.0.0** (2026-01-25)
- Initial implementation
- Four-component scoring system
- Time decay weighting
- CLI and Python API
- Comprehensive testing
- Automated cron scheduling

---

## Support

For issues or questions:
1. Check logs: `/var/log/tbaps/trust_calculator.log`
2. Run tests: `pytest tests/test_trust_calculator.py -v`
3. Review documentation: `docs/TRUST_CALCULATOR.md`
4. Check database: Verify signals and baselines exist

---

**Last Updated:** 2026-01-25  
**Version:** 1.0.0  
**Maintainer:** TBAPS Development Team
