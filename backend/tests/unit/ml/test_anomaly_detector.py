"""
Unit Tests for 3-Tier Anomaly Detection System
Tests statistical, rule-based, ML, and combined detection
"""

import pytest
import numpy as np
from datetime import datetime, time

from app.services.ml.anomaly_detector import (
    StatisticalAnomalyDetector,
    RuleBasedAnomalyDetector,
    MLAnomalyDetector,
    CombinedAnomalyDetector,
    AnomalyTier,
    AnomalySeverity,
    extract_ml_features,
    is_off_hours
)


# ============================================================================
# TIER 1: STATISTICAL DETECTION TESTS
# ============================================================================

@pytest.fixture
def statistical_detector():
    """Create statistical detector instance"""
    return StatisticalAnomalyDetector()


def test_statistical_anomaly_detected(statistical_detector):
    """Test statistical anomaly detection with clear anomaly"""
    # Value 4 standard deviations from mean
    result = statistical_detector.detect(
        value=140.0,
        baseline_mean=100.0,
        baseline_std=10.0,
        metric_name="test_metric"
    )
    
    assert result.is_anomaly is True
    assert result.tier == AnomalyTier.STATISTICAL
    assert result.details['z_score'] == 4.0
    assert result.confidence > 0.5


def test_statistical_no_anomaly(statistical_detector):
    """Test statistical detection with normal value"""
    # Value within 1 standard deviation
    result = statistical_detector.detect(
        value=105.0,
        baseline_mean=100.0,
        baseline_std=10.0,
        metric_name="test_metric"
    )
    
    assert result.is_anomaly is False
    assert result.details['z_score'] < 3.0


def test_statistical_zero_std(statistical_detector):
    """Test statistical detection with zero standard deviation"""
    result = statistical_detector.detect(
        value=100.0,
        baseline_mean=100.0,
        baseline_std=0.0,
        metric_name="test_metric"
    )
    
    assert result.is_anomaly is False
    assert result.confidence == 0.0


def test_statistical_severity_levels(statistical_detector):
    """Test severity levels based on Z-score"""
    # Critical: Z-score > 6
    result_critical = statistical_detector.detect(
        value=160.0, baseline_mean=100.0, baseline_std=10.0
    )
    assert result_critical.severity == AnomalySeverity.CRITICAL
    
    # High: Z-score > 5
    result_high = statistical_detector.detect(
        value=155.0, baseline_mean=100.0, baseline_std=10.0
    )
    assert result_high.severity == AnomalySeverity.HIGH
    
    # Medium: Z-score > 4
    result_medium = statistical_detector.detect(
        value=145.0, baseline_mean=100.0, baseline_std=10.0
    )
    assert result_medium.severity == AnomalySeverity.MEDIUM


def test_statistical_multiple_metrics(statistical_detector):
    """Test detection across multiple metrics"""
    values = {
        'metric1': 150.0,
        'metric2': 105.0,
        'metric3': 200.0
    }
    
    baselines = {
        'metric1': {'mean': 100.0, 'std': 10.0},
        'metric2': {'mean': 100.0, 'std': 10.0},
        'metric3': {'mean': 100.0, 'std': 20.0}
    }
    
    results = statistical_detector.detect_multiple(values, baselines)
    
    assert len(results) == 3
    assert results[0].is_anomaly is True  # metric1: Z=5
    assert results[1].is_anomaly is False  # metric2: Z=0.5
    assert results[2].is_anomaly is True  # metric3: Z=5


# ============================================================================
# TIER 2: RULE-BASED DETECTION TESTS
# ============================================================================

@pytest.fixture
def rule_detector():
    """Create rule-based detector instance"""
    return RuleBasedAnomalyDetector()


def test_rule_sensitive_access_without_vpn(rule_detector):
    """Test detection of sensitive access without VPN"""
    signals = {
        'vpn_connected': False,
        'accessing_sensitive_data': True
    }
    
    result = rule_detector.detect(signals)
    
    assert result.is_anomaly is True
    assert result.severity == AnomalySeverity.CRITICAL
    assert len(result.details['triggered_rules']) > 0
    assert any('vpn' in r['name'] for r in result.details['triggered_rules'])


def test_rule_multiple_failed_mfa(rule_detector):
    """Test detection of multiple failed MFA attempts"""
    signals = {
        'failed_mfa_attempts': 10
    }
    
    result = rule_detector.detect(signals)
    
    assert result.is_anomaly is True
    assert result.severity == AnomalySeverity.HIGH


def test_rule_off_hours_data_transfer(rule_detector):
    """Test detection of off-hours data transfer"""
    signals = {
        'off_hours': True,
        'large_data_download': True
    }
    
    result = rule_detector.detect(signals)
    
    assert result.is_anomaly is True
    assert result.severity == AnomalySeverity.HIGH


def test_rule_unusual_location_sensitive_access(rule_detector):
    """Test detection of unusual location with sensitive access"""
    signals = {
        'unusual_location': True,
        'accessing_sensitive_data': True
    }
    
    result = rule_detector.detect(signals)
    
    assert result.is_anomaly is True
    assert result.severity == AnomalySeverity.CRITICAL


def test_rule_data_exfiltration_pattern(rule_detector):
    """Test detection of data exfiltration pattern"""
    signals = {
        'large_data_download': True,
        'external_destination': True,
        'off_hours': True
    }
    
    result = rule_detector.detect(signals)
    
    assert result.is_anomaly is True
    assert result.severity == AnomalySeverity.CRITICAL


def test_rule_no_anomaly(rule_detector):
    """Test normal behavior with no rule violations"""
    signals = {
        'vpn_connected': True,
        'accessing_sensitive_data': False,
        'failed_mfa_attempts': 0,
        'off_hours': False
    }
    
    result = rule_detector.detect(signals)
    
    assert result.is_anomaly is False
    assert len(result.details['triggered_rules']) == 0


def test_rule_multiple_violations(rule_detector):
    """Test multiple rule violations increase confidence"""
    signals = {
        'vpn_connected': False,
        'accessing_sensitive_data': True,
        'failed_mfa_attempts': 10,
        'unusual_location': True
    }
    
    result = rule_detector.detect(signals)
    
    assert result.is_anomaly is True
    assert len(result.details['triggered_rules']) >= 2
    assert result.confidence > 0.7


# ============================================================================
# TIER 3: ML DETECTION TESTS
# ============================================================================

@pytest.fixture
def ml_detector():
    """Create ML detector instance"""
    return MLAnomalyDetector()


def test_ml_detector_initialization(ml_detector):
    """Test ML detector initializes correctly"""
    assert ml_detector is not None


def test_ml_train_and_detect(ml_detector):
    """Test ML training and detection"""
    # Generate training data (normal behavior)
    np.random.seed(42)
    normal_data = np.random.randn(100, 10) * 10 + 50
    
    # Train model
    feature_names = [f'feature_{i}' for i in range(10)]
    ml_detector.train(normal_data, feature_names)
    
    # Test normal sample
    normal_sample = np.array([50, 52, 48, 51, 49, 50, 51, 48, 52, 50])
    result_normal = ml_detector.detect(normal_sample)
    
    # Test anomalous sample (very different from training data)
    anomalous_sample = np.array([200, 200, 200, 200, 200, 200, 200, 200, 200, 200])
    result_anomaly = ml_detector.detect(anomalous_sample)
    
    # Anomalous sample should have different prediction than normal
    assert result_normal.tier == AnomalyTier.MACHINE_LEARNING
    assert result_anomaly.tier == AnomalyTier.MACHINE_LEARNING


def test_ml_feature_extraction():
    """Test ML feature extraction"""
    signals = {
        'login_count': 5,
        'failed_login_attempts': 2,
        'data_download_mb': 100,
        'admin_actions': 3,
        'sensitive_access_count': 1,
        'working_hours': 8,
        'location_changes': 0,
        'vpn_connected': True,
        'off_hours': False,
        'unusual_location': False
    }
    
    features = extract_ml_features(signals)
    
    assert isinstance(features, np.ndarray)
    assert len(features) == 10
    assert features[0] == 5  # login_count
    assert features[7] == 1  # vpn_connected (True = 1)


# ============================================================================
# COMBINED DETECTION TESTS
# ============================================================================

@pytest.fixture
def combined_detector():
    """Create combined detector instance"""
    return CombinedAnomalyDetector()


def test_combined_all_tiers_agree_anomaly(combined_detector):
    """Test when all three tiers detect anomaly"""
    signals = {
        'value': 150.0,  # Statistical anomaly
        'metric_name': 'test',
        'vpn_connected': False,  # Rule violation
        'accessing_sensitive_data': True,  # Rule violation
        'failed_mfa_attempts': 10  # Rule violation
    }
    
    baseline = {
        'mean': 100.0,
        'std': 10.0
    }
    
    ml_features = np.array([200, 200, 200, 200, 200, 200, 200, 200, 200, 200])
    
    result = combined_detector.detect(
        employee_id='emp_001',
        signals=signals,
        baseline=baseline,
        ml_features=ml_features
    )
    
    assert result.is_anomaly is True
    assert result.votes >= 2
    assert result.confidence > 0.5


def test_combined_two_tiers_agree(combined_detector):
    """Test when two tiers detect anomaly (voting threshold)"""
    signals = {
        'value': 150.0,  # Statistical anomaly
        'metric_name': 'test',
        'vpn_connected': False,  # Rule violation
        'accessing_sensitive_data': True  # Rule violation
    }
    
    baseline = {
        'mean': 100.0,
        'std': 10.0
    }
    
    result = combined_detector.detect(
        employee_id='emp_001',
        signals=signals,
        baseline=baseline
    )
    
    # At least 2 tiers should detect (statistical + rules)
    assert result.votes >= 2
    assert result.is_anomaly is True


def test_combined_one_tier_only(combined_detector):
    """Test when only one tier detects anomaly (not enough votes)"""
    signals = {
        'value': 105.0,  # Not statistical anomaly
        'metric_name': 'test',
        'vpn_connected': True,  # No rule violation
        'accessing_sensitive_data': False,
        'failed_mfa_attempts': 0
    }
    
    baseline = {
        'mean': 100.0,
        'std': 10.0
    }
    
    result = combined_detector.detect(
        employee_id='emp_001',
        signals=signals,
        baseline=baseline
    )
    
    # Should not be anomaly (need 2 of 3 votes)
    assert result.votes < 2
    assert result.is_anomaly is False


def test_combined_no_tiers_detect(combined_detector):
    """Test when no tiers detect anomaly"""
    signals = {
        'value': 100.0,
        'metric_name': 'test',
        'vpn_connected': True,
        'accessing_sensitive_data': False,
        'failed_mfa_attempts': 0,
        'off_hours': False
    }
    
    baseline = {
        'mean': 100.0,
        'std': 10.0
    }
    
    result = combined_detector.detect(
        employee_id='emp_001',
        signals=signals,
        baseline=baseline
    )
    
    assert result.votes == 0
    assert result.is_anomaly is False
    assert result.confidence == 0.0


def test_combined_severity_propagation(combined_detector):
    """Test that highest severity is propagated"""
    signals = {
        'value': 150.0,
        'metric_name': 'test',
        'vpn_connected': False,  # CRITICAL severity
        'accessing_sensitive_data': True,  # CRITICAL severity
        'unusual_location': True
    }
    
    baseline = {
        'mean': 100.0,
        'std': 10.0
    }
    
    result = combined_detector.detect(
        employee_id='emp_001',
        signals=signals,
        baseline=baseline
    )
    
    if result.is_anomaly:
        # Should have CRITICAL severity from rule violations
        assert result.severity == AnomalySeverity.CRITICAL


def test_combined_anomaly_types_collected(combined_detector):
    """Test that anomaly types are collected from all tiers"""
    signals = {
        'value': 150.0,
        'metric_name': 'test',
        'vpn_connected': False,
        'accessing_sensitive_data': True
    }
    
    baseline = {
        'mean': 100.0,
        'std': 10.0
    }
    
    result = combined_detector.detect(
        employee_id='emp_001',
        signals=signals,
        baseline=baseline
    )
    
    if result.is_anomaly:
        assert len(result.anomaly_types) > 0


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_is_off_hours_weekend():
    """Test off-hours detection for weekend"""
    # Saturday
    saturday = datetime(2024, 1, 6, 10, 0, 0)
    assert is_off_hours(saturday) is True


def test_is_off_hours_weekday_night():
    """Test off-hours detection for weekday night"""
    # Monday 8 PM
    monday_night = datetime(2024, 1, 1, 20, 0, 0)
    assert is_off_hours(monday_night) is True


def test_is_off_hours_weekday_morning():
    """Test off-hours detection for early morning"""
    # Monday 6 AM
    monday_morning = datetime(2024, 1, 1, 6, 0, 0)
    assert is_off_hours(monday_morning) is True


def test_is_business_hours():
    """Test business hours detection"""
    # Monday 10 AM
    monday_morning = datetime(2024, 1, 1, 10, 0, 0)
    assert is_off_hours(monday_morning) is False


def test_extract_ml_features_complete():
    """Test ML feature extraction with all signals"""
    signals = {
        'login_count': 10,
        'failed_login_attempts': 3,
        'data_download_mb': 500,
        'admin_actions': 5,
        'sensitive_access_count': 2,
        'working_hours': 9,
        'location_changes': 1,
        'vpn_connected': True,
        'off_hours': False,
        'unusual_location': False
    }
    
    features = extract_ml_features(signals)
    
    assert len(features) == 10
    assert features[0] == 10
    assert features[2] == 500
    assert features[7] == 1  # True converted to 1


def test_extract_ml_features_missing_values():
    """Test ML feature extraction with missing values"""
    signals = {}  # Empty signals
    
    features = extract_ml_features(signals)
    
    assert len(features) == 10
    # Should use default values
    assert features[7] == 1  # vpn_connected defaults to True


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def test_statistical_detection_performance(statistical_detector, benchmark):
    """Test statistical detection performance"""
    def detect():
        return statistical_detector.detect(150.0, 100.0, 10.0, "test")
    
    result = benchmark(detect)
    assert result is not None


def test_rule_detection_performance(rule_detector, benchmark):
    """Test rule-based detection performance"""
    signals = {
        'vpn_connected': False,
        'accessing_sensitive_data': True,
        'failed_mfa_attempts': 10
    }
    
    def detect():
        return rule_detector.detect(signals)
    
    result = benchmark(detect)
    assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
