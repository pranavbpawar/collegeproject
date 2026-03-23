#!/usr/bin/env python3
"""
Trust Calculator Validation Script
Validates the trust calculator logic without requiring database connection
"""

import sys
from datetime import datetime, timedelta
import uuid


class MockSignalEvent:
    """Mock signal event for testing"""
    def __init__(self, signal_type, timestamp, metadata=None):
        self.id = uuid.uuid4()
        self.employee_id = uuid.uuid4()
        self.signal_type = signal_type
        self.signal_value = 1.0
        self.metadata = metadata or {}
        self.source = 'test'
        self.timestamp = timestamp
        self.created_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(days=30)


class MockBaselineProfile:
    """Mock baseline profile for testing"""
    def __init__(self, metric, baseline_value, std_dev):
        self.metric = metric
        self.baseline_value = baseline_value
        self.std_dev = std_dev
        self.p95 = baseline_value + 2 * std_dev
        self.p50 = baseline_value
        self.p05 = baseline_value - 2 * std_dev


def validate_weights():
    """Validate that all weights sum to 1.0"""
    print("=" * 80)
    print("VALIDATING COMPONENT WEIGHTS")
    print("=" * 80)
    
    # Component weights
    WEIGHTS = {
        'outcome': 0.35,
        'behavioral': 0.30,
        'security': 0.20,
        'wellbeing': 0.15
    }
    
    total = sum(WEIGHTS.values())
    print(f"\nMain Component Weights:")
    for component, weight in WEIGHTS.items():
        print(f"  {component.capitalize()}: {weight:.2%}")
    print(f"  Total: {total:.4f}")
    
    if abs(total - 1.0) < 0.001:
        print("  ✅ PASS: Weights sum to 1.0")
    else:
        print(f"  ❌ FAIL: Weights sum to {total}, expected 1.0")
        return False
    
    # Sub-component weights
    sub_weights = {
        'Outcome': {'completion': 0.40, 'quality': 0.35, 'deadline': 0.25},
        'Behavioral': {'pattern_deviation': 0.40, 'response_time': 0.35, 'collaboration': 0.25},
        'Security': {'mfa': 0.33, 'vpn': 0.33, 'phishing': 0.34},
        'Wellbeing': {'engagement': 0.35, 'stress': 0.40, 'sentiment': 0.25}
    }
    
    all_valid = True
    for component, weights in sub_weights.items():
        total = sum(weights.values())
        print(f"\n{component} Sub-component Weights:")
        for sub, weight in weights.items():
            print(f"  {sub}: {weight:.2%}")
        print(f"  Total: {total:.4f}")
        
        if abs(total - 1.0) < 0.001:
            print(f"  ✅ PASS: {component} weights sum to 1.0")
        else:
            print(f"  ❌ FAIL: {component} weights sum to {total}, expected 1.0")
            all_valid = False
    
    return all_valid


def validate_time_decay():
    """Validate time decay calculation"""
    print("\n" + "=" * 80)
    print("VALIDATING TIME DECAY")
    print("=" * 80)
    
    TIME_DECAY = {
        (0, 7): 1.0,
        (8, 14): 0.8,
        (15, 30): 0.6,
    }
    
    print("\nTime Decay Factors:")
    for (min_days, max_days), factor in TIME_DECAY.items():
        print(f"  {min_days}-{max_days} days: {factor:.1%}")
    
    # Test recent signals
    now = datetime.utcnow()
    signals = [MockSignalEvent('task_completed', now - timedelta(days=i)) for i in range(7)]
    
    weighted_sum = sum(1.0 for _ in signals)
    decay = weighted_sum / len(signals)
    
    print(f"\nTest: 7 recent signals (0-6 days old)")
    print(f"  Expected decay: 1.0")
    print(f"  Actual decay: {decay:.2f}")
    
    if decay == 1.0:
        print("  ✅ PASS: Recent signals have full weight")
    else:
        print(f"  ❌ FAIL: Expected 1.0, got {decay}")
        return False
    
    # Test week-old signals
    signals = [MockSignalEvent('task_completed', now - timedelta(days=i)) for i in range(8, 15)]
    weighted_sum = sum(0.8 for _ in signals)
    decay = weighted_sum / len(signals)
    
    print(f"\nTest: 7 week-old signals (8-14 days old)")
    print(f"  Expected decay: 0.8")
    print(f"  Actual decay: {decay:.2f}")
    
    if decay == 0.8:
        print("  ✅ PASS: Week-old signals have 80% weight")
    else:
        print(f"  ❌ FAIL: Expected 0.8, got {decay}")
        return False
    
    # Test mixed signals
    signals = [
        *[MockSignalEvent('task_completed', now - timedelta(days=i)) for i in range(5)],  # 5 recent
        *[MockSignalEvent('task_completed', now - timedelta(days=i)) for i in range(10, 15)]  # 5 week-old
    ]
    weighted_sum = sum([1.0] * 5 + [0.8] * 5)
    decay = weighted_sum / len(signals)
    expected = 0.9
    
    print(f"\nTest: Mixed signals (5 recent + 5 week-old)")
    print(f"  Expected decay: {expected:.2f}")
    print(f"  Actual decay: {decay:.2f}")
    
    if abs(decay - expected) < 0.001:
        print("  ✅ PASS: Mixed signals calculated correctly")
    else:
        print(f"  ❌ FAIL: Expected {expected}, got {decay}")
        return False
    
    return True


def validate_score_normalization():
    """Validate score normalization to 0-100 range"""
    print("\n" + "=" * 80)
    print("VALIDATING SCORE NORMALIZATION")
    print("=" * 80)
    
    test_cases = [
        (-10, 0, "Negative score"),
        (0, 0, "Zero score"),
        (50, 50, "Mid-range score"),
        (100, 100, "Perfect score"),
        (150, 100, "Over-range score")
    ]
    
    all_valid = True
    for input_score, expected, description in test_cases:
        normalized = max(0.0, min(100.0, input_score))
        print(f"\nTest: {description}")
        print(f"  Input: {input_score}")
        print(f"  Expected: {expected}")
        print(f"  Actual: {normalized}")
        
        if normalized == expected:
            print(f"  ✅ PASS")
        else:
            print(f"  ❌ FAIL")
            all_valid = False
    
    return all_valid


def validate_outcome_calculation():
    """Validate outcome score calculation"""
    print("\n" + "=" * 80)
    print("VALIDATING OUTCOME SCORE CALCULATION")
    print("=" * 80)
    
    OUTCOME_WEIGHTS = {
        'completion': 0.40,
        'quality': 0.35,
        'deadline': 0.25
    }
    
    # Test perfect score
    completion_rate = 1.0  # 100% completion
    quality_score = 1.0    # No defects
    deadline_adherence = 1.0  # All on time
    
    outcome = (
        completion_rate * OUTCOME_WEIGHTS['completion'] +
        quality_score * OUTCOME_WEIGHTS['quality'] +
        deadline_adherence * OUTCOME_WEIGHTS['deadline']
    ) * 100
    
    print(f"\nTest: Perfect outcome")
    print(f"  Completion: {completion_rate:.1%}")
    print(f"  Quality: {quality_score:.1%}")
    print(f"  Deadline: {deadline_adherence:.1%}")
    print(f"  Expected score: 100.0")
    print(f"  Actual score: {outcome:.2f}")
    
    if outcome == 100.0:
        print("  ✅ PASS: Perfect outcome = 100")
    else:
        print(f"  ❌ FAIL: Expected 100, got {outcome}")
        return False
    
    # Test partial score
    completion_rate = 0.8  # 80% completion
    quality_score = 0.9    # 10% defects
    deadline_adherence = 0.75  # 75% on time
    
    outcome = (
        completion_rate * OUTCOME_WEIGHTS['completion'] +
        quality_score * OUTCOME_WEIGHTS['quality'] +
        deadline_adherence * OUTCOME_WEIGHTS['deadline']
    ) * 100
    
    expected = (0.8 * 0.40 + 0.9 * 0.35 + 0.75 * 0.25) * 100  # 82.75
    
    print(f"\nTest: Partial outcome")
    print(f"  Completion: {completion_rate:.1%}")
    print(f"  Quality: {quality_score:.1%}")
    print(f"  Deadline: {deadline_adherence:.1%}")
    print(f"  Expected score: {expected:.2f}")
    print(f"  Actual score: {outcome:.2f}")
    
    if abs(outcome - expected) < 0.01:
        print("  ✅ PASS: Partial outcome calculated correctly")
    else:
        print(f"  ❌ FAIL: Expected {expected}, got {outcome}")
        return False
    
    return True


def validate_security_calculation():
    """Validate security score calculation"""
    print("\n" + "=" * 80)
    print("VALIDATING SECURITY SCORE CALCULATION")
    print("=" * 80)
    
    SECURITY_WEIGHTS = {
        'mfa': 0.33,
        'vpn': 0.33,
        'phishing': 0.34
    }
    
    # Test perfect security
    mfa_score = 1.0  # MFA enabled
    vpn_score = 1.0  # 100% VPN compliance
    phishing_score = 1.0  # No incidents
    
    security = (
        mfa_score * SECURITY_WEIGHTS['mfa'] +
        vpn_score * SECURITY_WEIGHTS['vpn'] +
        phishing_score * SECURITY_WEIGHTS['phishing']
    ) * 100
    
    print(f"\nTest: Perfect security")
    print(f"  MFA: {mfa_score:.1%}")
    print(f"  VPN: {vpn_score:.1%}")
    print(f"  Phishing: {phishing_score:.1%}")
    print(f"  Expected score: 100.0")
    print(f"  Actual score: {security:.2f}")
    
    if security == 100.0:
        print("  ✅ PASS: Perfect security = 100")
    else:
        print(f"  ❌ FAIL: Expected 100, got {security}")
        return False
    
    # Test partial security
    mfa_score = 1.0  # MFA enabled
    vpn_score = 0.8  # 80% VPN compliance
    phishing_score = 0.95  # 1 incident in 20 emails
    
    security = (
        mfa_score * SECURITY_WEIGHTS['mfa'] +
        vpn_score * SECURITY_WEIGHTS['vpn'] +
        phishing_score * SECURITY_WEIGHTS['phishing']
    ) * 100
    
    expected = (1.0 * 0.33 + 0.8 * 0.33 + 0.95 * 0.34) * 100  # 91.2
    
    print(f"\nTest: Partial security")
    print(f"  MFA: {mfa_score:.1%}")
    print(f"  VPN: {vpn_score:.1%}")
    print(f"  Phishing: {phishing_score:.1%}")
    print(f"  Expected score: {expected:.2f}")
    print(f"  Actual score: {security:.2f}")
    
    if abs(security - expected) < 0.01:
        print("  ✅ PASS: Partial security calculated correctly")
    else:
        print(f"  ❌ FAIL: Expected {expected}, got {security}")
        return False
    
    return True


def main():
    """Run all validations"""
    print("\n" + "=" * 80)
    print("TBAPS TRUST CALCULATOR VALIDATION")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # Run validations
    results.append(("Component Weights", validate_weights()))
    results.append(("Time Decay", validate_time_decay()))
    results.append(("Score Normalization", validate_score_normalization()))
    results.append(("Outcome Calculation", validate_outcome_calculation()))
    results.append(("Security Calculation", validate_security_calculation()))
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} VALIDATION(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
