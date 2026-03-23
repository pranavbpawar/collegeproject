"""
Unit Tests for Email Analyzer
Tests sentiment analysis, urgency detection, and response time calculation
"""

import pytest
from datetime import datetime, timedelta
import uuid

from app.services.nlp.email_analyzer import (
    EmailAnalyzer,
    EmailMetadata,
    SentimentScore,
    EmailSignals,
    is_business_hours,
    calculate_response_time_score
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def analyzer():
    """Create EmailAnalyzer instance"""
    return EmailAnalyzer()


@pytest.fixture
def sample_email_data():
    """Create sample email metadata"""
    return {
        'email_id': str(uuid.uuid4()),
        'employee_id': str(uuid.uuid4()),
        'subject': 'Project update meeting',
        'sent_at': datetime.utcnow(),
        'recipient_count': 3,
        'replied_at': datetime.utcnow() + timedelta(minutes=30),
        'thread_id': str(uuid.uuid4()),
        'is_reply': True,
        'is_forwarded': False
    }


# ============================================================================
# SENTIMENT ANALYSIS TESTS
# ============================================================================

def test_sentiment_positive(analyzer):
    """Test positive sentiment detection"""
    subject = "Great work on the project! Excellent results"
    sentiment = analyzer.analyze_sentiment(subject)
    
    assert sentiment.label == 'positive'
    assert sentiment.compound > 0.1
    assert sentiment.positive > 0


def test_sentiment_negative(analyzer):
    """Test negative sentiment detection"""
    subject = "Failed deployment - critical issues found"
    sentiment = analyzer.analyze_sentiment(subject)
    
    assert sentiment.label == 'negative'
    assert sentiment.compound < -0.1
    assert sentiment.negative > 0


def test_sentiment_neutral(analyzer):
    """Test neutral sentiment detection"""
    subject = "Meeting scheduled for tomorrow at 2pm"
    sentiment = analyzer.analyze_sentiment(subject)
    
    assert sentiment.label == 'neutral'
    assert -0.1 <= sentiment.compound <= 0.1


def test_sentiment_empty_subject(analyzer):
    """Test sentiment with empty subject"""
    sentiment = analyzer.analyze_sentiment("")
    
    assert sentiment.label == 'neutral'
    assert sentiment.compound == 0.0


def test_sentiment_mixed(analyzer):
    """Test mixed sentiment"""
    subject = "Good progress but some concerns remain"
    sentiment = analyzer.analyze_sentiment(subject)
    
    # Should have both positive and negative components
    assert sentiment.positive > 0
    assert sentiment.negative > 0


# ============================================================================
# URGENCY DETECTION TESTS
# ============================================================================

def test_urgency_urgent_keyword(analyzer):
    """Test urgency detection with urgent keyword"""
    subject = "URGENT: Server down"
    is_urgent, score = analyzer.detect_urgency(subject)
    
    assert is_urgent is True
    assert score > 0.5


def test_urgency_asap_keyword(analyzer):
    """Test urgency detection with ASAP"""
    subject = "Need this ASAP please"
    is_urgent, score = analyzer.detect_urgency(subject)
    
    assert is_urgent is True
    assert score > 0.5


def test_urgency_multiple_exclamations(analyzer):
    """Test urgency detection with multiple exclamation marks"""
    subject = "NEED HELP NOW!!!"
    is_urgent, score = analyzer.detect_urgency(subject)
    
    assert is_urgent is True
    assert score > 0.5


def test_urgency_excessive_caps(analyzer):
    """Test urgency detection with excessive capitalization"""
    subject = "PLEASE REVIEW THIS IMMEDIATELY"
    is_urgent, score = analyzer.detect_urgency(subject)
    
    assert is_urgent is True


def test_urgency_deadline_pattern(analyzer):
    """Test urgency detection with deadline"""
    subject = "Report due today by 5pm"
    is_urgent, score = analyzer.detect_urgency(subject)
    
    assert is_urgent is True


def test_urgency_normal_subject(analyzer):
    """Test non-urgent subject"""
    subject = "Weekly team meeting notes"
    is_urgent, score = analyzer.detect_urgency(subject)
    
    assert is_urgent is False
    assert score < 0.5


def test_urgency_empty_subject(analyzer):
    """Test urgency with empty subject"""
    is_urgent, score = analyzer.detect_urgency("")
    
    assert is_urgent is False
    assert score == 0.0


# ============================================================================
# RESPONSE TIME TESTS
# ============================================================================

def test_response_time_calculation(analyzer):
    """Test response time calculation"""
    sent_at = datetime(2024, 1, 1, 10, 0, 0)
    replied_at = datetime(2024, 1, 1, 10, 30, 0)
    
    metadata = EmailMetadata(
        email_id=str(uuid.uuid4()),
        employee_id=str(uuid.uuid4()),
        subject="Test",
        sent_at=sent_at,
        recipient_count=1,
        replied_at=replied_at
    )
    
    response_time = analyzer.extract_response_time(metadata)
    
    assert response_time == 30.0  # 30 minutes


def test_response_time_no_reply(analyzer):
    """Test response time with no reply"""
    metadata = EmailMetadata(
        email_id=str(uuid.uuid4()),
        employee_id=str(uuid.uuid4()),
        subject="Test",
        sent_at=datetime.utcnow(),
        recipient_count=1,
        replied_at=None
    )
    
    response_time = analyzer.extract_response_time(metadata)
    
    assert response_time is None


def test_response_time_negative(analyzer):
    """Test response time with invalid data (replied before sent)"""
    sent_at = datetime(2024, 1, 1, 10, 30, 0)
    replied_at = datetime(2024, 1, 1, 10, 0, 0)  # Before sent
    
    metadata = EmailMetadata(
        email_id=str(uuid.uuid4()),
        employee_id=str(uuid.uuid4()),
        subject="Test",
        sent_at=sent_at,
        recipient_count=1,
        replied_at=replied_at
    )
    
    response_time = analyzer.extract_response_time(metadata)
    
    assert response_time is None  # Should return None for invalid data


def test_response_time_hours(analyzer):
    """Test response time in hours"""
    sent_at = datetime(2024, 1, 1, 10, 0, 0)
    replied_at = datetime(2024, 1, 1, 14, 30, 0)  # 4.5 hours later
    
    metadata = EmailMetadata(
        email_id=str(uuid.uuid4()),
        employee_id=str(uuid.uuid4()),
        subject="Test",
        sent_at=sent_at,
        recipient_count=1,
        replied_at=replied_at
    )
    
    response_time = analyzer.extract_response_time(metadata)
    
    assert response_time == 270.0  # 4.5 hours = 270 minutes


# ============================================================================
# COMMUNICATION PATTERN TESTS
# ============================================================================

def test_pattern_quick_responder(analyzer):
    """Test quick responder pattern"""
    pattern = analyzer.determine_communication_pattern(
        response_time=15.0,  # 15 minutes
        recipient_count=2,
        is_urgent=False
    )
    
    assert pattern == 'quick_responder'


def test_pattern_slow_responder(analyzer):
    """Test slow responder pattern"""
    pattern = analyzer.determine_communication_pattern(
        response_time=300.0,  # 5 hours
        recipient_count=2,
        is_urgent=False
    )
    
    assert pattern == 'slow_responder'


def test_pattern_broadcaster(analyzer):
    """Test broadcaster pattern"""
    pattern = analyzer.determine_communication_pattern(
        response_time=60.0,
        recipient_count=10,  # Many recipients
        is_urgent=False
    )
    
    assert pattern == 'broadcaster'


def test_pattern_urgent_communicator(analyzer):
    """Test urgent communicator pattern"""
    pattern = analyzer.determine_communication_pattern(
        response_time=60.0,
        recipient_count=2,
        is_urgent=True
    )
    
    assert pattern == 'urgent_communicator'


def test_pattern_normal(analyzer):
    """Test normal communication pattern"""
    pattern = analyzer.determine_communication_pattern(
        response_time=60.0,
        recipient_count=2,
        is_urgent=False
    )
    
    assert pattern == 'normal'


# ============================================================================
# WORD COUNT TESTS
# ============================================================================

def test_word_count_simple(analyzer):
    """Test word count with simple subject"""
    subject = "Meeting tomorrow at 2pm"
    count = analyzer.count_words(subject)
    
    assert count == 4


def test_word_count_with_punctuation(analyzer):
    """Test word count with punctuation"""
    subject = "Re: Project update - urgent!"
    count = analyzer.count_words(subject)
    
    assert count == 4  # Re, Project, update, urgent


def test_word_count_empty(analyzer):
    """Test word count with empty subject"""
    count = analyzer.count_words("")
    
    assert count == 0


def test_word_count_special_chars(analyzer):
    """Test word count with special characters"""
    subject = "Q1 2024 Results ($1.5M revenue)"
    count = analyzer.count_words(subject)
    
    assert count == 6


# ============================================================================
# FULL ANALYSIS TESTS
# ============================================================================

def test_analyze_email_metadata_complete(analyzer, sample_email_data):
    """Test complete email metadata analysis"""
    signals = analyzer.analyze_email_metadata(sample_email_data)
    
    assert signals.email_id == sample_email_data['email_id']
    assert signals.employee_id == sample_email_data['employee_id']
    assert signals.response_time_minutes == 30.0
    assert signals.recipient_count == 3
    assert signals.subject_word_count > 0
    assert signals.sentiment is not None
    assert isinstance(signals.is_urgent, bool)
    assert 0.0 <= signals.urgency_score <= 1.0


def test_analyze_urgent_email(analyzer):
    """Test analysis of urgent email"""
    email_data = {
        'email_id': str(uuid.uuid4()),
        'employee_id': str(uuid.uuid4()),
        'subject': 'URGENT: Production server down!!!',
        'sent_at': datetime.utcnow(),
        'recipient_count': 5,
        'replied_at': datetime.utcnow() + timedelta(minutes=5),
    }
    
    signals = analyzer.analyze_email_metadata(email_data)
    
    assert signals.is_urgent is True
    assert signals.urgency_score > 0.5
    assert signals.communication_pattern in ['quick_responder', 'urgent_communicator']


def test_analyze_positive_email(analyzer):
    """Test analysis of positive email"""
    email_data = {
        'email_id': str(uuid.uuid4()),
        'employee_id': str(uuid.uuid4()),
        'subject': 'Great job on the presentation!',
        'sent_at': datetime.utcnow(),
        'recipient_count': 1,
    }
    
    signals = analyzer.analyze_email_metadata(email_data)
    
    assert signals.sentiment.label == 'positive'
    assert signals.sentiment.compound > 0.1


# ============================================================================
# BATCH PROCESSING TESTS
# ============================================================================

def test_batch_analysis(analyzer):
    """Test batch email analysis"""
    email_batch = [
        {
            'email_id': str(uuid.uuid4()),
            'employee_id': str(uuid.uuid4()),
            'subject': 'Meeting tomorrow',
            'sent_at': datetime.utcnow(),
            'recipient_count': 2,
        },
        {
            'email_id': str(uuid.uuid4()),
            'employee_id': str(uuid.uuid4()),
            'subject': 'URGENT: Need help',
            'sent_at': datetime.utcnow(),
            'recipient_count': 1,
        }
    ]
    
    signals_list = analyzer.analyze_batch(email_batch)
    
    assert len(signals_list) == 2
    assert all(isinstance(s, EmailSignals) for s in signals_list)


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_is_business_hours_weekday():
    """Test business hours detection on weekday"""
    # Monday at 10 AM
    timestamp = datetime(2024, 1, 1, 10, 0, 0)  # Monday
    
    assert is_business_hours(timestamp) is True


def test_is_business_hours_weekend():
    """Test business hours detection on weekend"""
    # Saturday at 10 AM
    timestamp = datetime(2024, 1, 6, 10, 0, 0)  # Saturday
    
    assert is_business_hours(timestamp) is False


def test_is_business_hours_after_hours():
    """Test business hours detection after hours"""
    # Monday at 6 PM
    timestamp = datetime(2024, 1, 1, 18, 0, 0)
    
    assert is_business_hours(timestamp) is False


def test_response_time_score_fast():
    """Test response time score for fast response"""
    score = calculate_response_time_score(15.0)  # 15 minutes
    
    assert score == 100.0


def test_response_time_score_slow():
    """Test response time score for slow response"""
    score = calculate_response_time_score(600.0)  # 10 hours
    
    assert score == 50.0


def test_response_time_score_medium():
    """Test response time score for medium response"""
    score = calculate_response_time_score(90.0)  # 1.5 hours
    
    assert score == 80.0


# ============================================================================
# EDGE CASES
# ============================================================================

def test_analyze_minimal_data(analyzer):
    """Test analysis with minimal data"""
    email_data = {
        'email_id': str(uuid.uuid4()),
        'employee_id': str(uuid.uuid4()),
        'subject': '',
        'sent_at': datetime.utcnow(),
        'recipient_count': 1,
    }
    
    signals = analyzer.analyze_email_metadata(email_data)
    
    assert signals is not None
    assert signals.subject_word_count == 0
    assert signals.sentiment.label == 'neutral'


def test_analyze_very_long_subject(analyzer):
    """Test analysis with very long subject"""
    long_subject = "This is a very long subject line " * 20
    
    email_data = {
        'email_id': str(uuid.uuid4()),
        'employee_id': str(uuid.uuid4()),
        'subject': long_subject,
        'sent_at': datetime.utcnow(),
        'recipient_count': 1,
    }
    
    signals = analyzer.analyze_email_metadata(email_data)
    
    assert signals.subject_word_count > 100


def test_analyze_special_characters(analyzer):
    """Test analysis with special characters in subject"""
    subject = "Re: FW: [EXTERNAL] 🚨 Important Update 📊"
    
    email_data = {
        'email_id': str(uuid.uuid4()),
        'employee_id': str(uuid.uuid4()),
        'subject': subject,
        'sent_at': datetime.utcnow(),
        'recipient_count': 1,
    }
    
    signals = analyzer.analyze_email_metadata(email_data)
    
    assert signals is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
