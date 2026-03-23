# TBAPS Bias Detection - Quick Reference

## 🚀 Quick Commands

### Run Full Audit
```bash
cd /home/kali/Desktop/MACHINE/backend
python3 scripts/bias_audit_cli.py run-audit
```

### Detect Specific Bias
```bash
# Gender
python3 scripts/bias_audit_cli.py detect-gender

# Department
python3 scripts/bias_audit_cli.py detect-department

# Seniority
python3 scripts/bias_audit_cli.py detect-seniority

# Location
python3 scripts/bias_audit_cli.py detect-location
```

### Apply Mitigation
```bash
python3 scripts/bias_audit_cli.py mitigate
```

### View Reports
```bash
# Latest report
python3 scripts/bias_audit_cli.py report

# Specific date
python3 scripts/bias_audit_cli.py report --date 2026-01-28
```

---

## 🧪 Testing

### Run All Tests
```bash
cd /home/kali/Desktop/MACHINE/backend
pytest tests/test_bias_detector.py -v
```

### Run Specific Tests
```bash
# Statistical tests
pytest tests/test_bias_detector.py::TestBiasDetector::test_calculate_statistics_valid_scores -v

# Gender bias
pytest tests/test_bias_detector.py::TestBiasDetector::test_detect_gender_bias_with_bias -v

# Mitigation
pytest tests/test_bias_detector.py::TestBiasDetector::test_mitigate_bias_full_workflow -v
```

---

## 📊 Python API

### Basic Usage
```python
from app.services.bias_detector import BiasDetector

# Initialize
detector = BiasDetector()

# Run full audit
results = await detector.run_full_audit()

# Check for bias
if results['overall_bias_detected']:
    # Apply mitigation
    mitigation = await detector.mitigate_bias(results)
```

### Detect Specific Bias
```python
# Gender bias
gender_results = await detector.detect_gender_bias()

# Department bias
dept_results = await detector.detect_department_bias()

# Seniority bias
seniority_results = await detector.detect_seniority_bias()

# Location bias
location_results = await detector.detect_location_bias()
```

---

## ⚙️ Configuration

### Bias Thresholds
Edit in `app/services/bias_detector.py`:
```python
BIAS_THRESHOLDS = {
    'gender': 0.05,        # 5% disparity
    'department': 0.10,    # 10% disparity
    'seniority': 0.08,     # 8% disparity
    'location': 0.07,      # 7% disparity
    'race': 0.05,          # 5% disparity
}
```

### Minimum Sample Sizes
```python
MIN_SAMPLE_SIZES = {
    'gender': 10,
    'department': 5,
    'seniority': 5,
    'location': 5,
    'race': 10,
}
```

---

## 🔧 Installation

### Install Dependencies
```bash
cd /home/kali/Desktop/MACHINE/backend
pip install -r requirements.txt
```

### Install Cron Jobs
```bash
sudo cp scripts/bias_audit.cron /etc/cron.d/tbaps-bias-audit
sudo chmod 644 /etc/cron.d/tbaps-bias-audit
sudo systemctl restart cron
```

### Create Log Directory
```bash
sudo mkdir -p /var/log/tbaps
sudo chown -R $USER:$USER /var/log/tbaps
```

---

## 📁 File Locations

### Core Files
- **Engine:** `backend/app/services/bias_detector.py`
- **CLI:** `backend/scripts/bias_audit_cli.py`
- **Tests:** `backend/tests/test_bias_detector.py`
- **Cron:** `backend/scripts/bias_audit.cron`

### Documentation
- **Full Docs:** `backend/docs/BIAS_DETECTION.md`
- **Quick Ref:** `backend/docs/BIAS_DETECTION_QUICK_REF.md`
- **Delivery:** `BIAS_DETECTION_DELIVERY.md`

### Logs
- **Audit Logs:** `/var/log/tbaps/bias_audit.log`
- **Audit Reports:** `/var/log/tbaps/bias_audit_YYYYMMDD_HHMMSS.json`

---

## 🐛 Troubleshooting

### No demographic data
```python
# Add to employee metadata
employee.metadata = {
    'gender': 'female',
    'seniority': 'mid',
    'location': 'remote',
}
```

### Database connection error
```bash
# Check database
psql -U tbaps -d tbaps -c "SELECT COUNT(*) FROM employees;"
```

### Cron not running
```bash
# Check logs
sudo tail -f /var/log/tbaps/bias_audit.log

# Check cron status
sudo systemctl status cron
```

---

## 📞 Support

1. Check logs: `/var/log/tbaps/bias_audit.log`
2. Run tests: `pytest tests/test_bias_detector.py -v`
3. Review docs: `docs/BIAS_DETECTION.md`

---

**Version:** 1.0.0  
**Date:** 2026-01-28
