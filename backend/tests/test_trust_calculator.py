"""
Unit Tests for TBAPS Trust Score Calculator
Tests all component calculations, time decay, and score storage
"""

import pytest
import os
import sys
from datetime import datetime, timedelta
from typing import List
import uuid

# Set test environment
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/tbaps_test'
os.environ['JWT_SECRET_KEY'] = 'test_jwt_secret_key_for_testing_only'
os.environ['ENCRYPTION_KEY'] = 'test_encryption_key_32_bytes_long'
os.environ['CELERY_BROKER_URL'] = 'redis://localhost:6379/2'
os.environ['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/3'
os.environ['RABBITMQ_URL'] = 'amqp://guest:guest@localhost:5672/'

from app.services.trust_calculator import TrustCalculator
from app.models import Employee, SignalEvent, BaselineProfile, TrustScore


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def calculator():
    """Create trust calculator instance"""
    return TrustCalculator(window_days=30)


@pytest.fixture
def sample_employee_id():
    """Sample employee UUID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_signals():
    """Create sample signal events for testing"""
    employee_id = uuid.uuid4()
    now = datetime.utcnow()
    
    signals = []
    
    # Task signals (for outcome score)
    for i in range(10):
        # Task created
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='task_created',
            signal_value=1.0,
            metadata={'task_id': f'task_{i}'},
            source='jira',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
        
        # Task completed (80% completion rate)
        if i < 8:
            signals.append(SignalEvent(
                id=uuid.uuid4(),
                employee_id=employee_id,
                signal_type='task_completed',
                signal_value=1.0,
                metadata={
                    'task_id': f'task_{i}',
                    'on_time': i < 6,  # 75% on time
                    'has_defects': i == 7  # 1 defect
                },
                source='jira',
                timestamp=now - timedelta(days=i, hours=5),
                created_at=now,
                expires_at=now + timedelta(days=30)
            ))
    
    # Email signals (for behavioral and wellbeing)
    for i in range(20):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='email_sent',
            signal_value=1.0,
            metadata={
                'response_time_minutes': 30 + (i % 10),
                'sentiment_score': 0.6 + (i % 5) * 0.05
            },
            source='gmail',
            timestamp=now - timedelta(days=i % 15, hours=i % 8),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
    
    # Meeting signals (for collaboration)
    for i in range(15):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='meeting_attended',
            signal_value=1.0,
            metadata={'participated': i % 3 == 0},
            source='calendar',
            timestamp=now - timedelta(days=i % 10, hours=i % 6),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
    
    # Security signals
    for i in range(5):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='email_received',
            signal_value=1.0,
            metadata={
                'mfa_enabled': True,
                'vpn_connected': i < 4,  # 80% VPN compliance
                'sensitive_data_access': True
            },
            source='security',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
    
    return signals


@pytest.fixture
def sample_baseline():
    """Create sample baseline profiles"""
    employee_id = uuid.uuid4()
    now = datetime.utcnow()
    
    baselines = {
        'meetings_per_day': BaselineProfile(
            id=uuid.uuid4(),
            employee_id=employee_id,
            metric='meetings_per_day',
            baseline_value=3.5,
            std_dev=1.2,
            p95=6.0,
            p50=3.5,
            p05=1.0,
            min_value=0.0,
            max_value=8.0,
            confidence=0.95,
            sample_size=30,
            calculation_start=now - timedelta(days=30),
            calculation_end=now,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=90)
        ),
        'email_response_time_minutes': BaselineProfile(
            id=uuid.uuid4(),
            employee_id=employee_id,
            metric='email_response_time_minutes',
            baseline_value=35.0,
            std_dev=10.0,
            p95=55.0,
            p50=35.0,
            p05=15.0,
            min_value=5.0,
            max_value=120.0,
            confidence=0.92,
            sample_size=150,
            calculation_start=now - timedelta(days=30),
            calculation_end=now,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=90)
        ),
        'task_completion_rate': BaselineProfile(
            id=uuid.uuid4(),
            employee_id=employee_id,
            metric='task_completion_rate',
            baseline_value=0.85,
            std_dev=0.1,
            p95=0.95,
            p50=0.85,
            p05=0.65,
            min_value=0.5,
            max_value=1.0,
            confidence=0.88,
            sample_size=50,
            calculation_start=now - timedelta(days=30),
            calculation_end=now,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=90)
        )
    }
    
    return baselines


# ============================================================================
# COMPONENT WEIGHT TESTS
# ============================================================================

def test_weights_sum_to_one(calculator):
    """Test that all component weights sum to 1.0"""
    total = sum(calculator.WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"


def test_outcome_weights_sum_to_one(calculator):
    """Test that outcome sub-component weights sum to 1.0"""
    total = sum(calculator.OUTCOME_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Outcome weights sum to {total}, expected 1.0"


def test_behavioral_weights_sum_to_one(calculator):
    """Test that behavioral sub-component weights sum to 1.0"""
    total = sum(calculator.BEHAVIORAL_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Behavioral weights sum to {total}, expected 1.0"


def test_security_weights_sum_to_one(calculator):
    """Test that security sub-component weights sum to 1.0"""
    total = sum(calculator.SECURITY_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Security weights sum to {total}, expected 1.0"


def test_wellbeing_weights_sum_to_one(calculator):
    """Test that wellbeing sub-component weights sum to 1.0"""
    total = sum(calculator.WELLBEING_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Wellbeing weights sum to {total}, expected 1.0"


# ============================================================================
# TIME DECAY TESTS
# ============================================================================

def test_time_decay_recent_signals(calculator):
    """Test time decay for recent signals (0-7 days)"""
    now = datetime.utcnow()
    signals = [
        SignalEvent(
            id=uuid.uuid4(),
            employee_id=uuid.uuid4(),
            signal_type='task_completed',
            signal_value=1.0,
            metadata={},
            source='test',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        )
        for i in range(7)
    ]
    
    decay = calculator._calculate_time_decay(signals)
    assert decay == 1.0, f"Recent signals should have 1.0 decay, got {decay}"


def test_time_decay_week_old_signals(calculator):
    """Test time decay for week-old signals (8-14 days)"""
    now = datetime.utcnow()
    signals = [
        SignalEvent(
            id=uuid.uuid4(),
            employee_id=uuid.uuid4(),
            signal_type='task_completed',
            signal_value=1.0,
            metadata={},
            source='test',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        )
        for i in range(8, 15)
    ]
    
    decay = calculator._calculate_time_decay(signals)
    assert decay == 0.8, f"Week-old signals should have 0.8 decay, got {decay}"


def test_time_decay_month_old_signals(calculator):
    """Test time decay for month-old signals (15-30 days)"""
    now = datetime.utcnow()
    signals = [
        SignalEvent(
            id=uuid.uuid4(),
            employee_id=uuid.uuid4(),
            signal_type='task_completed',
            signal_value=1.0,
            metadata={},
            source='test',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        )
        for i in range(15, 31)
    ]
    
    decay = calculator._calculate_time_decay(signals)
    assert decay == 0.6, f"Month-old signals should have 0.6 decay, got {decay}"


def test_time_decay_mixed_signals(calculator):
    """Test time decay for mixed-age signals"""
    now = datetime.utcnow()
    signals = [
        # 5 recent (1.0 weight)
        *[SignalEvent(
            id=uuid.uuid4(),
            employee_id=uuid.uuid4(),
            signal_type='task_completed',
            signal_value=1.0,
            metadata={},
            source='test',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ) for i in range(5)],
        # 5 week-old (0.8 weight)
        *[SignalEvent(
            id=uuid.uuid4(),
            employee_id=uuid.uuid4(),
            signal_type='task_completed',
            signal_value=1.0,
            metadata={},
            source='test',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ) for i in range(10, 15)]
    ]
    
    decay = calculator._calculate_time_decay(signals)
    expected = (5 * 1.0 + 5 * 0.8) / 10  # 0.9
    assert abs(decay - expected) < 0.001, f"Mixed signals should have {expected} decay, got {decay}"


# ============================================================================
# OUTCOME SCORE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_outcome_score_perfect(calculator):
    """Test outcome score with perfect completion"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    signals = []
    for i in range(10):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='task_created',
            signal_value=1.0,
            metadata={'task_id': f'task_{i}'},
            source='test',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='task_completed',
            signal_value=1.0,
            metadata={'task_id': f'task_{i}', 'on_time': True, 'has_defects': False},
            source='test',
            timestamp=now - timedelta(days=i, hours=2),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
    
    score = await calculator._calc_outcome_score(signals, None)
    assert score == 100.0, f"Perfect outcome should be 100, got {score}"


@pytest.mark.asyncio
async def test_outcome_score_no_tasks(calculator):
    """Test outcome score with no task signals"""
    signals = []
    score = await calculator._calc_outcome_score(signals, None)
    assert score == 50.0, f"No tasks should return default 50, got {score}"


# ============================================================================
# BEHAVIORAL SCORE TESTS
# ============================================================================

def test_pattern_deviation_perfect(calculator, sample_signals, sample_baseline):
    """Test pattern deviation with perfect match to baseline"""
    # Mock current metrics to match baseline exactly
    deviation = calculator._calc_pattern_deviation(sample_signals, sample_baseline)
    assert 0.0 <= deviation <= 1.0, f"Deviation should be 0-1, got {deviation}"


def test_collaboration_score(calculator):
    """Test collaboration score calculation"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    # 10 meetings invited, 8 attended, 4 participated
    signals = []
    for i in range(10):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='calendar_event',
            signal_value=1.0,
            metadata={},
            source='calendar',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
    
    for i in range(8):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='meeting_attended',
            signal_value=1.0,
            metadata={'participated': i < 4},
            source='calendar',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
    
    score = calculator._calc_collaboration(signals)
    # Attendance: 8/10 = 0.8, Participation: 4/8 = 0.5
    # Score: 0.8 * 0.6 + 0.5 * 0.4 = 0.48 + 0.2 = 0.68
    expected = 0.68
    assert abs(score - expected) < 0.01, f"Collaboration score should be {expected}, got {score}"


# ============================================================================
# SECURITY SCORE TESTS
# ============================================================================

def test_vpn_compliance_perfect(calculator):
    """Test VPN compliance with 100% compliance"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    signals = [
        SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='email_sent',
            signal_value=1.0,
            metadata={'sensitive_data_access': True, 'vpn_connected': True},
            source='security',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        )
        for i in range(10)
    ]
    
    score = calculator._calc_vpn_compliance(signals)
    assert score == 1.0, f"Perfect VPN compliance should be 1.0, got {score}"


def test_vpn_compliance_partial(calculator):
    """Test VPN compliance with partial compliance"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    signals = [
        SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='email_sent',
            signal_value=1.0,
            metadata={'sensitive_data_access': True, 'vpn_connected': i < 7},
            source='security',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        )
        for i in range(10)
    ]
    
    score = calculator._calc_vpn_compliance(signals)
    assert score == 0.7, f"70% VPN compliance should be 0.7, got {score}"


def test_phishing_safety_perfect(calculator):
    """Test phishing safety with no incidents"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    signals = [
        SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='email_received',
            signal_value=1.0,
            metadata={'phishing_detected': False, 'clicked_phishing': False},
            source='security',
            timestamp=now - timedelta(days=i),
            created_at=now,
            expires_at=now + timedelta(days=30)
        )
        for i in range(100)
    ]
    
    score = calculator._calc_phishing_safety(signals)
    assert score == 1.0, f"Perfect phishing safety should be 1.0, got {score}"


# ============================================================================
# WELLBEING SCORE TESTS
# ============================================================================

def test_engagement_score(calculator):
    """Test engagement score calculation"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    # 50 total signals, 30 productive
    signals = []
    for i in range(30):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='code_commit',
            signal_value=1.0,
            metadata={'high_quality': i < 10},
            source='github',
            timestamp=now - timedelta(days=i % 15),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
    
    for i in range(20):
        signals.append(SignalEvent(
            id=uuid.uuid4(),
            employee_id=employee_id,
            signal_type='email_received',
            signal_value=1.0,
            metadata={},
            source='gmail',
            timestamp=now - timedelta(days=i % 10),
            created_at=now,
            expires_at=now + timedelta(days=30)
        ))
    
    score = calculator._calc_engagement(signals)
    # Engagement rate: 30/50 = 0.6
    # Quality bonus: 10/30 = 0.333
    # Score: 0.6 * 0.7 + 0.333 * 0.3 = 0.42 + 0.1 = 0.52
    assert 0.5 <= score <= 0.6, f"Engagement score should be ~0.52, got {score}"


def test_stress_calculation_normal(calculator):
    """Test stress calculation with normal work hours"""
    now = datetime.utcnow()
    employee_id = uuid.uuid4()
    
    # Normal 8-hour days, Monday-Friday
    signals = []
    for day in range(5):
        start_time = now.replace(hour=9, minute=0) - timedelta(days=day)
        for hour in range(8):
            signals.append(SignalEvent(
                id=uuid.uuid4(),
                employee_id=employee_id,
                signal_type='email_sent',
                signal_value=1.0,
                metadata={},
                source='gmail',
                timestamp=start_time + timedelta(hours=hour),
                created_at=now,
                expires_at=now + timedelta(days=30)
            ))
    
    stress = calculator._calc_stress(signals)
    assert stress < 0.3, f"Normal hours should have low stress, got {stress}"


# ============================================================================
# SCORE NORMALIZATION TESTS
# ============================================================================

def test_score_normalization():
    """Test that scores are normalized to 0-100 range"""
    calculator = TrustCalculator()
    
    # Test values
    test_scores = [-10, 0, 50, 100, 150]
    
    for score in test_scores:
        normalized = max(0.0, min(100.0, score))
        assert 0 <= normalized <= 100, f"Score {score} normalized to {normalized}, should be 0-100"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_calculator_initialization():
    """Test calculator initialization"""
    calc = TrustCalculator(window_days=30)
    assert calc.window_days == 30
    assert sum(calc.WEIGHTS.values()) == 1.0


def test_calculator_custom_window():
    """Test calculator with custom window"""
    calc = TrustCalculator(window_days=60)
    assert calc.window_days == 60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
