# TBAPS Intervention Engine - Quick Reference

## 🚀 Quick Commands

### Individual Recommendations
```bash
cd /home/kali/Desktop/MACHINE/backend
python3 scripts/intervention_cli.py recommend --employee-id abc-123
```

### Team Recommendations
```bash
python3 scripts/intervention_cli.py recommend-team --department engineering
```

### Critical Interventions Only
```bash
python3 scripts/intervention_cli.py list-critical
```

### Comprehensive Report
```bash
python3 scripts/intervention_cli.py report
```

---

## 💻 Python API

### Generate Recommendations
```python
from app.services.intervention_engine import InterventionEngine

# Initialize engine
engine = InterventionEngine()

# Get recommendations for employee
interventions = await engine.recommend_interventions(employee_id)

# Check for critical interventions
critical = [i for i in interventions if i['priority'] == 'critical']

# Get team recommendations
team_interventions = await engine.recommend_team_interventions(
    department='engineering'
)
```

### Track Interventions
```python
from app.services.intervention_tracker import (
    InterventionTracker,
    InterventionStatus,
    InterventionOutcome,
)

# Initialize tracker
tracker = InterventionTracker()

# Create intervention
intervention_id = await tracker.create_intervention(
    employee_id=emp_id,
    category='wellness',
    priority='high',
    title='High Burnout Risk',
    description='Employee showing high burnout risk',
    actions=['Schedule 1:1', 'Offer time off'],
    urgency_days=7,
)

# Update status
await tracker.update_status(
    intervention_id,
    InterventionStatus.IN_PROGRESS,
    notes='Started wellness check-in'
)

# Complete intervention
await tracker.complete_intervention(
    intervention_id,
    InterventionOutcome.SUCCESSFUL,
    final_metrics={'burnout_risk': 0.3},
    completion_notes='Employee feeling much better'
)

# Get analytics
analytics = await tracker.get_analytics()
```

### Use Action Templates
```python
from app.services.action_templates import ActionTemplates

# Get template
template = ActionTemplates.get_template('wellness', 'critical')

# Display actions
for action in template['actions']:
    print(f"Step {action['step']}: {action['action']}")
    print(f"  Owner: {action['owner']}")
    print(f"  Duration: {action['duration']}")
```

---

## 📊 Intervention Types

### Wellness Interventions
- **Critical Burnout** (3 days urgency)
  - Immediate 1:1, time off, 50% workload reduction
- **High Burnout** (7 days urgency)
  - Wellness programs, 25% workload reduction
- **Medium Burnout** (14 days urgency)
  - Preventive wellness, work-life balance review

### Performance Interventions
- **Performance Support** (14 days urgency)
  - Skills assessment, training, mentoring

### Engagement Interventions
- **Engagement & Retention** (7 days urgency)
  - Career planning, growth opportunities, stay interview

### Development Interventions
- **Leadership Development** (30 days urgency)
  - Leadership training, mentorship role, strategic projects

### Team Interventions
- **Team Wellness** (7 days urgency)
  - Team wellness day, workload review, flexible work
- **Team Performance** (14 days urgency)
  - Skills assessment, group training, process improvement

---

## 🎯 Risk Thresholds

### Burnout Risk
```python
CRITICAL: 0.8-1.0  # Immediate action (3 days)
HIGH:     0.7-0.8  # Urgent support (7 days)
MEDIUM:   0.5-0.7  # Preventive action (14 days)
LOW:      0-0.5    # Monitoring only
```

### Performance Trend
```python
DECLINING:  < -0.1  # Performance support needed
STABLE:     -0.1 to 0.1  # No intervention
IMPROVING:  > 0.1   # Development opportunities
```

### Engagement
```python
LOW:   < 0.4  # Engagement intervention
MEDIUM: 0.4-0.7  # Monitoring
HIGH:  > 0.7  # Development opportunities
```

### Trust Score
```python
LOW:  < 50.0  # Engagement intervention
HIGH: > 80.0  # Development opportunities
```

---

## 📁 File Locations

### Core Files
- **Engine:** `backend/app/services/intervention_engine.py`
- **Templates:** `backend/app/services/action_templates.py`
- **Tracker:** `backend/app/services/intervention_tracker.py`
- **CLI:** `backend/scripts/intervention_cli.py`
- **Tests:** `backend/tests/test_intervention_engine.py`

### Documentation
- **Full Docs:** `backend/docs/INTERVENTION_ENGINE.md`
- **Delivery:** `INTERVENTION_ENGINE_DELIVERY.md`
- **Quick Ref:** `backend/docs/INTERVENTION_ENGINE_QUICK_REF.md`

### Logs
- **Engine Logs:** `/var/log/tbaps/intervention_engine.log`

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/test_intervention_engine.py -v
```

### Run Specific Tests
```bash
# Burnout prediction
pytest tests/test_intervention_engine.py::TestInterventionEngine::test_predict_burnout_high_risk -v

# Performance trend
pytest tests/test_intervention_engine.py::TestInterventionEngine::test_performance_trend_improving -v

# Intervention creation
pytest tests/test_intervention_engine.py::TestInterventionEngine::test_create_critical_burnout_intervention -v
```

---

## 🐛 Troubleshooting

### No interventions generated
```python
# Check employee data
- Verify employee has trust scores
- Check signal data exists
- Ensure employee status is 'active'
```

### Incorrect risk levels
```python
# Adjust thresholds in intervention_engine.py
THRESHOLDS = {
    'burnout_critical': 0.8,  # Adjust as needed
    'burnout_high': 0.7,
    # ...
}
```

### Database errors
```bash
# Check database connection
psql -U tbaps -d tbaps -c "SELECT COUNT(*) FROM employees;"
```

### Check logs
```bash
tail -f /var/log/tbaps/intervention_engine.log
```

---

## 📞 Support

1. **Check Logs:** `/var/log/tbaps/intervention_engine.log`
2. **Run Tests:** `pytest tests/test_intervention_engine.py -v`
3. **Review Docs:** `docs/INTERVENTION_ENGINE.md`

---

**Version:** 1.0.0  
**Date:** 2026-01-28  
**Role:** People Operations Lead
