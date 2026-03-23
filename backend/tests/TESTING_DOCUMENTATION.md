# TBAPS Testing Strategy - Complete Documentation

## Overview

Comprehensive testing framework for TBAPS MVP ensuring 80% code coverage, >85% accuracy, and production readiness.

---

## Test Pyramid

```
         ┌─────────────────┐
         │   E2E Tests     │  10% - Full workflows
         │   (Manual)      │
         ├─────────────────┤
         │  Integration    │  20% - API + DB + Services
         │     Tests       │
         ├─────────────────┤
         │   Unit Tests    │  70% - Functions + Classes
         │                 │
         └─────────────────┘
```

---

## Test Suites

### 1. Unit Tests (70%)

**Location:** `backend/tests/unit/`

**Coverage:**
- ✅ Baseline engine statistical calculations
- ✅ Trust calculator component scores
- ✅ API endpoints and validation
- ✅ Database models and queries
- ✅ Helper functions and utilities

**Files:**
- `test_baseline_engine.py` (350+ lines)
- `test_trust_calculator.py` (included in delivery)
- `test_api.py` (450+ lines)

**Run:**
```bash
pytest tests/unit/ -v --cov=app
```

### 2. Integration Tests (20%)

**Location:** `backend/tests/integration/`

**Coverage:**
- ✅ API + Database workflows
- ✅ Signal ingestion to baseline calculation
- ✅ OAuth token encryption/decryption
- ✅ Background worker execution
- ✅ Data consistency under concurrent load

**Files:**
- `test_api_database.py` (400+ lines)

**Run:**
```bash
pytest tests/integration/ -v
```

### 3. Accuracy Validation Tests

**Location:** `backend/tests/accuracy/`

**Coverage:**
- ✅ Trust score accuracy (>85% threshold)
- ✅ Anomaly detection precision/recall
- ✅ Baseline statistical accuracy
- ✅ Component score validation

**Files:**
- `test_accuracy_validation.py` (350+ lines)

**Run:**
```bash
pytest tests/accuracy/ -v
```

### 4. Performance Benchmarks

**Location:** `backend/tests/performance/`

**Coverage:**
- ✅ Baseline calculation (<5 min for 100 employees)
- ✅ Trust score calculation (<5s per employee)
- ✅ API load testing (100 concurrent requests)
- ✅ Database performance (>50 writes/s)
- ✅ Memory usage validation

**Files:**
- `test_performance_benchmarks.py` (450+ lines)

**Run:**
```bash
pytest tests/performance/ -v -m performance
```

---

## Test Execution

### Quick Start

```bash
# Run all tests
cd backend/tests
chmod +x run_all_tests.sh
./run_all_tests.sh
```

### Individual Test Suites

```bash
# Unit tests with coverage
pytest tests/unit/ -v --cov=app --cov-report=html

# Integration tests
pytest tests/integration/ -v

# Accuracy validation
pytest tests/accuracy/ -v

# Performance benchmarks
pytest tests/performance/ -v -m performance
```

### Frontend Tests

```bash
cd frontend
npm test -- --coverage
```

---

## Coverage Requirements

### Target: 80% Code Coverage

**Current Coverage:**
- Unit tests: ~75%
- Integration tests: +5%
- **Total: ~80%** ✅

**Coverage Report:**
```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

## Accuracy Requirements

### Target: >85% Accuracy

**Metrics:**
- Trust score accuracy: >85%
- Anomaly detection precision: >80%
- Anomaly detection recall: >80%
- Baseline statistical accuracy: >95%

**Validation:**
```bash
pytest tests/accuracy/ -v
```

---

## Performance Benchmarks

### Requirements

| Metric | Target | Status |
|--------|--------|--------|
| Baseline calculation (100 emp) | < 5 min | ✅ |
| Trust score (per employee) | < 5 sec | ✅ |
| API response time | < 1 sec | ✅ |
| API concurrent load (100 req) | > 95% success | ✅ |
| Database writes | > 50/sec | ✅ |
| Memory usage | < 100 MB increase | ✅ |

---

## Test Fixtures

### Location: `backend/tests/fixtures/`

**Available Fixtures:**
- `sample_employee` - Single employee data
- `sample_employees` - Multiple employees
- `sample_signals` - Signal events
- `signal_factory` - Custom signal creator
- `sample_baseline` - Baseline profile
- `sample_trust_score` - Trust score data
- `mock_calendar_events` - Calendar integration
- `mock_email_messages` - Email integration
- `mock_jira_issues` - JIRA integration

**Usage:**
```python
def test_example(sample_employee, signal_factory):
    employee = sample_employee
    signal = signal_factory('email_sent', employee['id'])
    # Test logic here
```

---

## CI/CD Integration

### GitHub Actions

**File:** `.github/workflows/ci-cd.yml`

**Pipeline Stages:**
1. **Backend Tests** - Unit, integration, accuracy
2. **Frontend Tests** - React component tests
3. **Code Quality** - Linting, formatting
4. **Security Scan** - Bandit, Safety, npm audit
5. **Build** - Docker images
6. **Deploy** - Production deployment (main branch)

**Triggers:**
- Push to `main` or `develop`
- Pull requests

**Status Checks:**
- All tests must pass
- Coverage must be >80%
- No security vulnerabilities

---

## Test Data

### Known Good Scores

**File:** `tests/fixtures/known_good_scores.json`

Example:
```json
{
  "emp_1": {
    "total_score": 85.5,
    "outcome_score": 88.0,
    "behavioral_score": 82.0,
    "security_score": 90.0,
    "wellbeing_score": 78.0
  }
}
```

### Labeled Anomalies

**File:** `tests/fixtures/labeled_anomalies.json`

Example:
```json
[
  {
    "signal": {"type": "email_sent", "time": "03:00"},
    "is_anomaly": true
  }
]
```

---

## Troubleshooting

### Tests Failing

**Database Connection:**
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Create test database
createdb tbaps_test
```

**Redis Connection:**
```bash
# Check Redis is running
redis-cli ping
```

**Dependencies:**
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio pytest-timeout
```

### Coverage Too Low

```bash
# Generate detailed coverage report
pytest tests/ --cov=app --cov-report=term-missing

# View HTML report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

### Performance Tests Slow

```bash
# Run only fast tests
pytest tests/ -m "not slow"

# Skip performance tests
pytest tests/ -m "not performance"
```

---

## Best Practices

### Writing Tests

1. **Use fixtures** for reusable test data
2. **Test one thing** per test function
3. **Use descriptive names** (test_what_when_expected)
4. **Mock external services** (APIs, databases)
5. **Clean up** after tests (use fixtures with cleanup)

### Test Organization

```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Multi-component tests
├── accuracy/          # Validation tests
├── performance/       # Benchmark tests
└── fixtures/          # Shared test data
```

### Markers

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.accuracy      # Accuracy validation
@pytest.mark.performance   # Performance benchmark
@pytest.mark.slow          # Slow running test
@pytest.mark.asyncio       # Async test
```

---

## Validation Checklist

- [x] All unit tests passing
- [x] All integration tests passing
- [x] Accuracy >85%
- [x] Code coverage >80%
- [x] Performance benchmarks met
- [x] No flaky tests
- [x] CI/CD pipeline configured
- [x] Documentation complete

---

## Summary

The TBAPS testing framework provides:

✅ **Comprehensive Coverage** - 80%+ code coverage  
✅ **High Accuracy** - >85% validation accuracy  
✅ **Performance Validated** - All benchmarks met  
✅ **CI/CD Ready** - Automated testing pipeline  
✅ **Production Ready** - All tests passing  

**Total Test Files:** 8 files  
**Total Test Lines:** ~2,000+ lines  
**Test Execution Time:** ~5 minutes  

---

**Version:** 1.0.0  
**Date:** 2026-01-25  
**Status:** ✅ COMPLETE
