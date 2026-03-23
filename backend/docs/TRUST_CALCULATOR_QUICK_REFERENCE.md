# Trust Calculator Quick Reference

## Quick Start

```bash
# 1. Calculate scores for all employees
python3 scripts/trust_calculator_cli.py calculate-all

# 2. Check specific employee
python3 scripts/trust_calculator_cli.py get-score --employee-id abc123

# 3. View top performers
python3 scripts/trust_calculator_cli.py list-scores --limit 20

# 4. View logs
tail -f /var/log/tbaps/trust_calculator.log
```

## Score Components

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| **Outcome** | 35% | Task completion, quality, deadlines |
| **Behavioral** | 30% | Pattern stability, response times, collaboration |
| **Security** | 20% | MFA, VPN compliance, phishing safety |
| **Wellbeing** | 15% | Engagement, stress levels, sentiment |

## Score Interpretation

| Range | Meaning | Action |
|-------|---------|--------|
| 90-100 | Excellent | Recognize and reward |
| 70-89 | Good | Normal performance |
| 50-69 | Needs Improvement | Offer support |
| Below 50 | Critical | Immediate intervention |

## Time Decay

| Age | Weight | Description |
|-----|--------|-------------|
| 0-7 days | 100% | Recent data |
| 8-14 days | 80% | Week old |
| 15-30 days | 60% | Month old |
| 30+ days | 0% | Ignored |

## CLI Commands

```bash
# Calculate all employees
trust_calculator_cli.py calculate-all [--window-days 30]

# Calculate single employee
trust_calculator_cli.py calculate-employee --employee-id ID [--window-days 30]

# Get latest score
trust_calculator_cli.py get-score --employee-id ID

# List scores
trust_calculator_cli.py list-scores [--limit 10] [--sort-by total]
```

## Cron Schedule

```
0 6 * * *     # Daily at 6 AM - all employees
0 7 * * 0     # Weekly Sunday 7 AM - full refresh
0 * * * *     # Hourly - new employees
```

## Python API

```python
from app.services.trust_calculator import TrustCalculator

calculator = TrustCalculator(window_days=30)

# Calculate all
summary = await calculator.calculate_daily_scores()

# Calculate one
score = await calculator.calculate_trust_score(employee_id)

# Access scores
print(f"Total: {score['total']}")
print(f"Outcome: {score['outcome']}")
print(f"Behavioral: {score['behavioral']}")
print(f"Security: {score['security']}")
print(f"Wellbeing: {score['wellbeing']}")
```

## Troubleshooting

**No scores calculated?**
- Check signal data: `SELECT COUNT(*) FROM signal_events`
- Check baselines: `SELECT COUNT(*) FROM baseline_profiles`
- Establish baselines: `python3 scripts/baseline_cli.py establish-all`

**Low scores across board?**
- Verify integrations are syncing
- Check signal metadata completeness
- Recalculate baselines with more data

**Slow calculation?**
- Check database indexes
- Monitor during off-peak hours
- Review query performance

## Files

| File | Purpose |
|------|---------|
| `app/services/trust_calculator.py` | Main engine |
| `scripts/trust_calculator_cli.py` | CLI tool |
| `scripts/trust_calculator.cron` | Cron config |
| `tests/test_trust_calculator.py` | Unit tests |
| `docs/TRUST_CALCULATOR.md` | Full docs |

---

**Version:** 1.0.0  
**Docs:** `backend/docs/TRUST_CALCULATOR.md`
