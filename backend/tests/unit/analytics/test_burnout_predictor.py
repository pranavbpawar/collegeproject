"""
Unit Tests for Burnout Prediction System
Tests all indicators, scoring, and recommendations
"""

import pytest
from datetime import datetime, timedelta

from app.services.analytics.burnout_predictor import (
    BurnoutPredictor,
    BurnoutRiskLevel,
    RecommendationPriority,
    BurnoutIndicators
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def predictor():
    """Create burnout predictor instance"""
    return BurnoutPredictor()


@pytest.fixture
def high_burnout_signals():
    """Signals indicating high burnout risk"""
    return {
        'weekly_hours': [55, 54, 56, 53],  # Excessive hours
        'late_night_work_count': 15,
        'weekend_work_count': 8,
        'vacation_days_used': 1,
        'vacation_days_baseline': 10,
        'meeting_attendance_trend': -0.30,  # Low engagement
        'collaboration_trend': -0.25,
        'email_response_trend': -0.28,
        'task_completion_trend': -0.22,
        'completion_rate_trend': -0.25,  # Productivity decline
        'quality_trend': -0.20,
        'deadline_miss_trend': 0.35,
        'rework_ratio': 0.40,
        'very_late_night_count': 18,  # Sleep issues
        'early_morning_count': 12,
        'sleep_pattern_irregularity': 0.80,
        'urgency_trend': 0.35,  # High stress
        'sentiment_trend': -0.30,
        'anomaly_trend': 0.32,
        'context_switches_per_day': 60
    }


@pytest.fixture
def low_burnout_signals():
    """Signals indicating low burnout risk"""
    return {
        'weekly_hours': [40, 42, 41, 40],
        'late_night_work_count': 1,
        'weekend_work_count': 0,
        'vacation_days_used': 8,
        'vacation_days_baseline': 10,
        'meeting_attendance_trend': 0.05,
        'collaboration_trend': 0.03,
        'email_response_trend': 0.02,
        'task_completion_trend': 0.04,
        'completion_rate_trend': 0.05,
        'quality_trend': 0.03,
        'deadline_miss_trend': -0.05,
        'rework_ratio': 0.10,
        'very_late_night_count': 0,
        'early_morning_count': 0,
        'sleep_pattern_irregularity': 0.15,
        'urgency_trend': 0.02,
        'sentiment_trend': 0.05,
        'anomaly_trend': 0.01,
        'context_switches_per_day': 20
    }


# ============================================================================
# WORK HOURS INDICATOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_excessive_hours_detected(predictor, high_burnout_signals):
    """Test detection of excessive work hours"""
    is_excessive, score = await predictor.calc_work_hours('emp_001', high_burnout_signals)
    
    assert is_excessive is True
    assert score > 50.0


@pytest.mark.asyncio
async def test_normal_hours(predictor, low_burnout_signals):
    """Test normal work hours"""
    is_excessive, score = await predictor.calc_work_hours('emp_001', low_burnout_signals)
    
    assert is_excessive is False
    assert score < 50.0


@pytest.mark.asyncio
async def test_late_night_work_scoring(predictor):
    """Test late night work contributes to score"""
    signals = {
        'weekly_hours': [42],
        'late_night_work_count': 15,  # Many late nights
        'weekend_work_count': 0,
        'vacation_days_used': 5,
        'vacation_days_baseline': 10
    }
    
    is_excessive, score = await predictor.calc_work_hours('emp_001', signals)
    
    assert score > 20.0  # Late nights should add points


@pytest.mark.asyncio
async def test_weekend_work_scoring(predictor):
    """Test weekend work contributes to score"""
    signals = {
        'weekly_hours': [42],
        'late_night_work_count': 0,
        'weekend_work_count': 8,  # Many weekend days
        'vacation_days_used': 5,
        'vacation_days_baseline': 10
    }
    
    is_excessive, score = await predictor.calc_work_hours('emp_001', signals)
    
    assert score > 15.0  # Weekend work should add points


# ============================================================================
# ENGAGEMENT INDICATOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_low_engagement_detected(predictor, high_burnout_signals):
    """Test detection of low engagement"""
    is_low, score = await predictor.calc_engagement_trend('emp_001', high_burnout_signals)
    
    assert is_low is True
    assert score > 50.0


@pytest.mark.asyncio
async def test_normal_engagement(predictor, low_burnout_signals):
    """Test normal engagement"""
    is_low, score = await predictor.calc_engagement_trend('emp_001', low_burnout_signals)
    
    assert is_low is False
    assert score < 50.0


@pytest.mark.asyncio
async def test_meeting_attendance_decline(predictor):
    """Test meeting attendance decline contributes to score"""
    signals = {
        'meeting_attendance_trend': -0.30,  # 30% decline
        'collaboration_trend': 0.0,
        'email_response_trend': 0.0,
        'task_completion_trend': 0.0
    }
    
    is_low, score = await predictor.calc_engagement_trend('emp_001', signals)
    
    assert score > 20.0


# ============================================================================
# PRODUCTIVITY INDICATOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_productivity_decline_detected(predictor, high_burnout_signals):
    """Test detection of productivity decline"""
    is_declining, score = await predictor.calc_productivity_trend('emp_001', high_burnout_signals)
    
    assert is_declining is True
    assert score > 50.0


@pytest.mark.asyncio
async def test_normal_productivity(predictor, low_burnout_signals):
    """Test normal productivity"""
    is_declining, score = await predictor.calc_productivity_trend('emp_001', low_burnout_signals)
    
    assert is_declining is False
    assert score < 50.0


@pytest.mark.asyncio
async def test_high_rework_ratio(predictor):
    """Test high rework ratio contributes to score"""
    signals = {
        'completion_rate_trend': 0.0,
        'quality_trend': 0.0,
        'deadline_miss_trend': 0.0,
        'rework_ratio': 0.35  # 35% rework
    }
    
    is_declining, score = await predictor.calc_productivity_trend('emp_001', signals)
    
    assert score > 10.0


# ============================================================================
# SLEEP QUALITY INDICATOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_sleep_issues_detected(predictor, high_burnout_signals):
    """Test detection of sleep issues"""
    has_issues, score = await predictor.calc_sleep_quality('emp_001', high_burnout_signals)
    
    assert has_issues is True
    assert score > 50.0


@pytest.mark.asyncio
async def test_good_sleep(predictor, low_burnout_signals):
    """Test good sleep quality"""
    has_issues, score = await predictor.calc_sleep_quality('emp_001', low_burnout_signals)
    
    assert has_issues is False
    assert score < 50.0


@pytest.mark.asyncio
async def test_very_late_nights(predictor):
    """Test very late nights (after 11 PM) contribute to score"""
    signals = {
        'very_late_night_count': 15,  # Many very late nights
        'early_morning_count': 0,
        'sleep_pattern_irregularity': 0.2
    }
    
    has_issues, score = await predictor.calc_sleep_quality('emp_001', signals)
    
    assert score > 30.0


@pytest.mark.asyncio
async def test_irregular_sleep_pattern(predictor):
    """Test irregular sleep pattern contributes to score"""
    signals = {
        'very_late_night_count': 0,
        'early_morning_count': 0,
        'sleep_pattern_irregularity': 0.8  # Very irregular
    }
    
    has_issues, score = await predictor.calc_sleep_quality('emp_001', signals)
    
    assert score > 20.0


# ============================================================================
# STRESS INDICATOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_high_stress_detected(predictor, high_burnout_signals):
    """Test detection of high stress"""
    is_high, score = await predictor.calc_stress_indicators('emp_001', high_burnout_signals)
    
    assert is_high is True
    assert score > 50.0


@pytest.mark.asyncio
async def test_normal_stress(predictor, low_burnout_signals):
    """Test normal stress levels"""
    is_high, score = await predictor.calc_stress_indicators('emp_001', low_burnout_signals)
    
    assert is_high is False
    assert score < 50.0


@pytest.mark.asyncio
async def test_sentiment_decline(predictor):
    """Test sentiment decline contributes to score"""
    signals = {
        'urgency_trend': 0.0,
        'sentiment_trend': -0.25,  # 25% decline
        'anomaly_trend': 0.0,
        'context_switches_per_day': 20
    }
    
    is_high, score = await predictor.calc_stress_indicators('emp_001', signals)
    
    assert score > 20.0


@pytest.mark.asyncio
async def test_high_context_switching(predictor):
    """Test high context switching contributes to score"""
    signals = {
        'urgency_trend': 0.0,
        'sentiment_trend': 0.0,
        'anomaly_trend': 0.0,
        'context_switches_per_day': 60  # Very high
    }
    
    is_high, score = await predictor.calc_stress_indicators('emp_001', signals)
    
    assert score > 10.0


# ============================================================================
# BURNOUT SCORE TESTS
# ============================================================================

def test_burnout_score_calculation(predictor):
    """Test burnout score calculation"""
    indicators = BurnoutIndicators(
        excessive_hours=True,
        excessive_hours_score=80.0,
        low_engagement=True,
        engagement_score=70.0,
        productivity_decline=True,
        productivity_score=60.0,
        sleep_issues=True,
        sleep_score=75.0,
        high_stress=True,
        stress_score=65.0
    )
    
    score = predictor.calculate_burnout_score(indicators)
    
    # Should be weighted average
    expected = (80*0.25 + 70*0.20 + 60*0.20 + 75*0.20 + 65*0.15)
    assert abs(score - expected) < 1.0


def test_burnout_score_range(predictor):
    """Test burnout score is in valid range"""
    indicators = BurnoutIndicators(
        excessive_hours=True,
        excessive_hours_score=100.0,
        low_engagement=True,
        engagement_score=100.0,
        productivity_decline=True,
        productivity_score=100.0,
        sleep_issues=True,
        sleep_score=100.0,
        high_stress=True,
        stress_score=100.0
    )
    
    score = predictor.calculate_burnout_score(indicators)
    
    assert 0.0 <= score <= 100.0


# ============================================================================
# RISK LEVEL TESTS
# ============================================================================

def test_risk_level_critical(predictor):
    """Test critical risk level"""
    risk = predictor.determine_risk_level(85.0)
    assert risk == BurnoutRiskLevel.CRITICAL


def test_risk_level_high(predictor):
    """Test high risk level"""
    risk = predictor.determine_risk_level(60.0)
    assert risk == BurnoutRiskLevel.HIGH


def test_risk_level_moderate(predictor):
    """Test moderate risk level"""
    risk = predictor.determine_risk_level(35.0)
    assert risk == BurnoutRiskLevel.MODERATE


def test_risk_level_low(predictor):
    """Test low risk level"""
    risk = predictor.determine_risk_level(15.0)
    assert risk == BurnoutRiskLevel.LOW


# ============================================================================
# RECOMMENDATION TESTS
# ============================================================================

def test_recommendations_for_excessive_hours(predictor):
    """Test recommendations for excessive hours"""
    indicators = BurnoutIndicators(
        excessive_hours=True,
        excessive_hours_score=80.0,
        low_engagement=False,
        engagement_score=20.0,
        productivity_decline=False,
        productivity_score=20.0,
        sleep_issues=False,
        sleep_score=20.0,
        high_stress=False,
        stress_score=20.0
    )
    
    recommendations = predictor.generate_recommendations(indicators, BurnoutRiskLevel.HIGH)
    
    assert len(recommendations) > 0
    assert any('work hours' in r.action.lower() for r in recommendations)


def test_recommendations_for_sleep_issues(predictor):
    """Test recommendations for sleep issues"""
    indicators = BurnoutIndicators(
        excessive_hours=False,
        excessive_hours_score=20.0,
        low_engagement=False,
        engagement_score=20.0,
        productivity_decline=False,
        productivity_score=20.0,
        sleep_issues=True,
        sleep_score=80.0,
        high_stress=False,
        stress_score=20.0
    )
    
    recommendations = predictor.generate_recommendations(indicators, BurnoutRiskLevel.MODERATE)
    
    assert len(recommendations) > 0
    assert any('sleep' in r.action.lower() for r in recommendations)


def test_urgent_recommendation_for_critical(predictor):
    """Test urgent recommendation for critical risk"""
    indicators = BurnoutIndicators(
        excessive_hours=True,
        excessive_hours_score=90.0,
        low_engagement=True,
        engagement_score=85.0,
        productivity_decline=True,
        productivity_score=80.0,
        sleep_issues=True,
        sleep_score=85.0,
        high_stress=True,
        stress_score=80.0
    )
    
    recommendations = predictor.generate_recommendations(indicators, BurnoutRiskLevel.CRITICAL)
    
    assert len(recommendations) > 0
    assert recommendations[0].priority == RecommendationPriority.URGENT


def test_recommendations_sorted_by_priority(predictor):
    """Test recommendations are sorted by priority"""
    indicators = BurnoutIndicators(
        excessive_hours=True,
        excessive_hours_score=80.0,
        low_engagement=True,
        engagement_score=70.0,
        productivity_decline=True,
        productivity_score=60.0,
        sleep_issues=True,
        sleep_score=50.0,
        high_stress=True,
        stress_score=40.0
    )
    
    recommendations = predictor.generate_recommendations(indicators, BurnoutRiskLevel.HIGH)
    
    # Check that priorities are in order
    priority_order = {
        RecommendationPriority.URGENT: 0,
        RecommendationPriority.HIGH: 1,
        RecommendationPriority.MEDIUM: 2,
        RecommendationPriority.LOW: 3
    }
    
    for i in range(len(recommendations) - 1):
        assert priority_order[recommendations[i].priority] <= priority_order[recommendations[i+1].priority]


# ============================================================================
# CONFIDENCE TESTS
# ============================================================================

def test_confidence_with_complete_data(predictor):
    """Test confidence with complete data"""
    signals = {
        'weekly_hours': [45],
        'meeting_attendance_trend': -0.1,
        'completion_rate_trend': -0.05,
        'sentiment_trend': -0.08
    }
    
    indicators = BurnoutIndicators(
        excessive_hours=True,
        excessive_hours_score=60.0,
        low_engagement=True,
        engagement_score=55.0,
        productivity_decline=True,
        productivity_score=50.0,
        sleep_issues=False,
        sleep_score=30.0,
        high_stress=False,
        stress_score=25.0
    )
    
    confidence = predictor.calculate_confidence(signals, indicators)
    
    assert confidence > 0.7  # High confidence with complete data and agreement


def test_confidence_with_incomplete_data(predictor):
    """Test confidence with incomplete data"""
    signals = {
        'weekly_hours': [45]
    }
    
    indicators = BurnoutIndicators(
        excessive_hours=True,
        excessive_hours_score=60.0,
        low_engagement=False,
        engagement_score=20.0,
        productivity_decline=False,
        productivity_score=20.0,
        sleep_issues=False,
        sleep_score=20.0,
        high_stress=False,
        stress_score=20.0
    )
    
    confidence = predictor.calculate_confidence(signals, indicators)
    
    assert confidence < 0.7  # Lower confidence with incomplete data


# ============================================================================
# FULL PREDICTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_prediction_high_risk(predictor, high_burnout_signals):
    """Test full prediction with high burnout risk"""
    # Mock the get_signals method
    async def mock_get_signals(employee_id, days):
        return high_burnout_signals
    
    predictor.get_signals = mock_get_signals
    
    prediction = await predictor.predict_burnout('emp_001')
    
    assert prediction.burnout_score > 50.0
    assert prediction.risk_level in [BurnoutRiskLevel.HIGH, BurnoutRiskLevel.CRITICAL]
    assert len(prediction.recommendations) > 0
    assert prediction.confidence > 0.5


@pytest.mark.asyncio
async def test_full_prediction_low_risk(predictor, low_burnout_signals):
    """Test full prediction with low burnout risk"""
    async def mock_get_signals(employee_id, days):
        return low_burnout_signals
    
    predictor.get_signals = mock_get_signals
    
    prediction = await predictor.predict_burnout('emp_001')
    
    assert prediction.burnout_score < 50.0
    assert prediction.risk_level in [BurnoutRiskLevel.LOW, BurnoutRiskLevel.MODERATE]


@pytest.mark.asyncio
async def test_prediction_date_is_4_weeks_ahead(predictor):
    """Test prediction date is 4 weeks in the future"""
    async def mock_get_signals(employee_id, days):
        return {}
    
    predictor.get_signals = mock_get_signals
    
    prediction = await predictor.predict_burnout('emp_001')
    
    expected_date = datetime.utcnow() + timedelta(days=28)
    assert abs((prediction.prediction_date - expected_date).total_seconds()) < 60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
