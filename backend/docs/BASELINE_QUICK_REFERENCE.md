# Baseline Engine Quick Reference

## Quick Start

```bash
# 1. Establish baselines for all employees
python3 scripts/baseline_cli.py establish-all

# 2. Check specific employee
python3 scripts/baseline_cli.py get-baseline --employee-id abc123

# 3. View logs
tail -f /var/log/tbaps/baseline.log
```

## Metrics Calculated

| Metric | Description | Use Case |
|--------|-------------|----------|
| `meetings_per_day` | Daily meeting count | Detect meeting overload |
| `email_response_time_minutes` | Avg email response time | Detect communication delays |
| `task_completion_rate` | % tasks completed | Detect productivity changes |
| `work_hours_start` | Typical start time | Detect schedule changes |
| `work_hours_end` | Typical end time | Detect overwork |
| `context_switches_per_day` | Task switching frequency | Detect focus issues |
| `collaboration_intensity` | Collaborative activities | Detect isolation |
| `average_meeting_duration_minutes` | Avg meeting length | Detect efficiency |

## Statistics Calculated

- **Mean:** Baseline value
- **Std Dev:** Variability (for anomaly detection)
- **Median (p50):** Middle value
- **p05, p25, p75, p95:** Percentiles for outlier detection
- **Min/Max:** Range
- **Sample Size:** Number of data points
- **Confidence:** Data completeness (50%-100%)

## Confidence Interpretation

| Score | Meaning | Action |
|-------|---------|--------|
| 100% | Full 30 days, excellent data | Use baseline with high confidence |
| 80-99% | Good data, minor gaps | Use baseline normally |
| 60-79% | Acceptable, some gaps | Use with caution |
| 50-59% | Minimum acceptable | Monitor closely |
| <50% | Insufficient data | Baseline not created |

## CLI Commands

```bash
# Establish all baselines
baseline_cli.py establish-all [--days 30] [--min-days 14]

# Establish single employee
baseline_cli.py establish-employee --employee-id ID [--days 30]

# Get baseline
baseline_cli.py get-baseline --employee-id ID [--metric METRIC]
```

## Cron Schedule

```
0 3 * * *     # Daily at 3 AM - all employees
0 4 * * 0     # Weekly Sunday 4 AM - full refresh
0 */6 * * *   # Every 6 hours - new employees
```

## Python API

```python
from app.services.baseline_engine import BaselineEngine

engine = BaselineEngine(min_days=14, target_days=30)

# Establish all
summary = await engine.establish_all_baselines(days_lookback=30)

# Establish one
success = await engine.establish_employee_baseline(employee_id)

# Get baseline
baselines = await engine.get_employee_baseline(employee_id)
```

## Troubleshooting

**No baselines created?**
- Check signal data: `SELECT COUNT(*) FROM signal_events`
- Check employees: `SELECT COUNT(*) FROM employees WHERE status='active'`
- Review logs: `tail -f /var/log/tbaps/baseline.log`

**Low confidence scores?**
- Verify integrations are syncing
- Check signal density per employee
- Consider lowering `--min-days` temporarily

**Slow processing?**
- Check database indexes
- Monitor during off-peak hours
- Review query performance

## Files

| File | Purpose |
|------|---------|
| `app/services/baseline_engine.py` | Main engine |
| `scripts/baseline_cli.py` | CLI tool |
| `scripts/baseline.cron` | Cron config |
| `tests/test_baseline_engine.py` | Unit tests |
| `docs/BASELINE_ENGINE.md` | Full docs |

---

**Version:** 1.0.0  
**Docs:** `backend/docs/BASELINE_ENGINE.md`
