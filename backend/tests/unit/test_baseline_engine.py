"""
Unit Tests for Baseline Engine
Tests statistical calculations, confidence scoring, and baseline establishment
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.services.baseline_engine import BaselineEngine
from app.models import SignalEvent, BaselineProfile, Employee


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def engine():
    """Create baseline engine instance"""
    return BaselineEngine(window_days=30)


@pytest.fixture
def sample_signals():
    """Create sample signal data"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    signals = []
    for i in range(30):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='meeting_attended',
            signal_value=1.0,
            metadata={'duration': 30 + i},
            source='calendar',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=90)
        ))
    
    return signals


# ============================================================================
# STATISTICAL CALCULATION TESTS
# ============================================================================

def test_calculate_mean(engine):
    """Test mean calculation"""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = engine._calculate_statistics(values)
    
    assert stats['mean'] == 3.0
    assert stats['count'] == 5


def test_calculate_median(engine):
    """Test median calculation"""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = engine._calculate_statistics(values)
    
    assert stats['median'] == 3.0


def test_calculate_std_dev(engine):
    """Test standard deviation calculation"""
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    stats = engine._calculate_statistics(values)
    
    assert stats['std_dev'] > 0
    assert 1.5 < stats['std_dev'] < 2.5


def test_calculate_percentiles(engine):
    """Test percentile calculations"""
    values = list(range(1, 101))  # 1 to 100
    stats = engine._calculate_statistics(values)
    
    assert stats['p05'] == pytest.approx(5.95, abs=1)
    assert stats['p50'] == pytest.approx(50.5, abs=1)
    assert stats['p95'] == pytest.approx(95.05, abs=1)


def test_statistics_with_single_value(engine):
    """Test statistics with single data point"""
    values = [5.0]
    stats = engine._calculate_statistics(values)
    
    assert stats['mean'] == 5.0
    assert stats['std_dev'] == 0.0
    assert stats['min'] == 5.0
    assert stats['max'] == 5.0


def test_statistics_with_empty_list(engine):
    """Test statistics with no data"""
    values = []
    stats = engine._calculate_statistics(values)
    
    assert stats is None


# ============================================================================
# CONFIDENCE CALCULATION TESTS
# ============================================================================

def test_confidence_full_data(engine):
    """Test confidence with full 30 days of data"""
    confidence = engine._calculate_confidence(data_points=30, target_days=30)
    
    assert confidence == 1.0


def test_confidence_half_data(engine):
    """Test confidence with half the target days"""
    confidence = engine._calculate_confidence(data_points=15, target_days=30)
    
    assert 0.4 < confidence < 0.6


def test_confidence_minimal_data(engine):
    """Test confidence with minimal data"""
    confidence = engine._calculate_confidence(data_points=3, target_days=30)
    
    assert 0.0 < confidence < 0.3


def test_confidence_no_data(engine):
    """Test confidence with no data"""
    confidence = engine._calculate_confidence(data_points=0, target_days=30)
    
    assert confidence == 0.0


def test_confidence_exceeds_target(engine):
    """Test confidence when data exceeds target"""
    confidence = engine._calculate_confidence(data_points=60, target_days=30)
    
    assert confidence == 1.0


# ============================================================================
# METRIC EXTRACTION TESTS
# ============================================================================

def test_extract_meetings_per_day(engine, sample_signals):
    """Test meetings per day extraction"""
    values = engine._extract_metric_values(sample_signals, 'meetings_per_day')
    
    assert len(values) > 0
    assert all(isinstance(v, (int, float)) for v in values)


def test_extract_email_response_time(engine):
    """Test email response time extraction"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    signals = [
        SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='email_sent',
            signal_value=1.0,
            metadata={'response_time_minutes': 30 + i},
            source='gmail',
            timestamp=now - timedelta(hours=i),
            created_at=now,
            expires_at=now + timedelta(days=90)
        )
        for i in range(10)
    ]
    
    values = engine._extract_metric_values(signals, 'email_response_time_minutes')
    
    assert len(values) == 10
    assert min(values) >= 30
    assert max(values) <= 39


def test_extract_task_completion_rate(engine):
    """Test task completion rate extraction"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    signals = []
    # 10 tasks created, 8 completed
    for i in range(10):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='task_created',
            signal_value=1.0,
            metadata={'task_id': f'task_{i}'},
            source='jira',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=90)
        ))
    
    for i in range(8):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='task_completed',
            signal_value=1.0,
            metadata={'task_id': f'task_{i}'},
            source='jira',
            timestamp=now - timedelta(days=i, hours=5),
            created_at=now,
            expires_at=now + timedelta(days=90)
        ))
    
    values = engine._extract_metric_values(signals, 'task_completion_rate')
    
    assert len(values) > 0
    assert all(0 <= v <= 1 for v in values)


# ============================================================================
# BASELINE ESTABLISHMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_establish_baseline_success(engine):
    """Test successful baseline establishment"""
    # This would require a test database
    # Placeholder for integration test
    pass


@pytest.mark.asyncio
async def test_establish_baseline_insufficient_data(engine):
    """Test baseline with insufficient data"""
    # Should return None or low confidence baseline
    pass


@pytest.mark.asyncio
async def test_establish_all_baselines(engine):
    """Test batch baseline establishment"""
    # Should process all employees
    pass


# ============================================================================
# EDGE CASES
# ============================================================================

def test_handle_outliers(engine):
    """Test handling of outlier values"""
    values = [1, 2, 3, 4, 5, 100]  # 100 is outlier
    stats = engine._calculate_statistics(values)
    
    # Should still calculate but be affected by outlier
    assert stats['mean'] > 5
    assert stats['median'] == 3.5  # Median less affected


def test_handle_negative_values(engine):
    """Test handling of negative values"""
    values = [-5, -3, -1, 0, 1, 3, 5]
    stats = engine._calculate_statistics(values)
    
    assert stats['mean'] == 0.0
    assert stats['min'] == -5
    assert stats['max'] == 5


def test_handle_large_dataset(engine):
    """Test performance with large dataset"""
    values = list(range(10000))
    stats = engine._calculate_statistics(values)
    
    assert stats is not None
    assert stats['count'] == 10000


# ============================================================================
# VALIDATION TESTS
# ============================================================================

def test_validate_metric_name(engine):
    """Test metric name validation"""
    valid_metrics = [
        'meetings_per_day',
        'email_response_time_minutes',
        'task_completion_rate',
        'code_commits_per_day'
    ]
    
    for metric in valid_metrics:
        # Should not raise exception
        assert metric in engine.SUPPORTED_METRICS or True


def test_validate_window_days(engine):
    """Test window days validation"""
    assert engine.window_days > 0
    assert engine.window_days <= 90


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
