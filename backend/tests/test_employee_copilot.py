"""
Tests for Employee Copilot

Comprehensive test suite for AI-powered employee insights and recommendations.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import uuid

from app.services.employee_copilot import EmployeeCopilot


class TestEmployeeCopilot:
    """Test EmployeeCopilot class"""
    
    @pytest.fixture
    def copilot(self):
        """Create copilot instance"""
        return EmployeeCopilot()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def sample_signals(self):
        """Create sample signal events"""
        signals = []
        base_time = datetime.utcnow() - timedelta(days=15)
        
        for i in range(30):
            signal = Mock()
            signal.employee_id = uuid.uuid4()
            signal.timestamp = base_time + timedelta(days=i // 2, hours=i % 12 + 8)
            signal.signal_type = ['task_completed', 'meeting_attended', 'code_commit'][i % 3]
            signals.append(signal)
        
        return signals
    
    # ========================================================================
    # PRODUCTIVITY PATTERN TESTS
    # ========================================================================
    
    def test_analyze_productivity_patterns_peak_hours(self, copilot, sample_signals):
        """Test peak hours identification"""
        patterns = copilot._analyze_productivity_patterns(sample_signals)
        
        assert 'peak_hours' in patterns
        assert isinstance(patterns['peak_hours'], tuple)
        assert len(patterns['peak_hours']) == 2
        assert 0 <= patterns['peak_hours'][0] < 24
        assert 0 <= patterns['peak_hours'][1] <= 24
    
    def test_analyze_productivity_patterns_consistency(self, copilot):
        """Test consistency detection"""
        # Create consistent signals
        signals = []
        for i in range(30):
            signal = Mock()
            signal.timestamp = datetime.utcnow() - timedelta(days=i)
            signal.signal_type = 'task_completed'
            signals.append(signal)
        
        patterns = copilot._analyze_productivity_patterns(signals)
        
        # Should detect consistent performance
        assert patterns.get('consistent_performance', False)
    
    def test_analyze_productivity_patterns_empty(self, copilot):
        """Test with no signals"""
        patterns = copilot._analyze_productivity_patterns([])
        
        assert patterns == {}
    
    # ========================================================================
    # TREND FLAG TESTS
    # ========================================================================
    
    def test_identify_trend_flags_reduced_meetings(self, copilot):
        """Test reduced meetings flag"""
        signals = []
        for i in range(100):
            signal = Mock()
            signal.timestamp = datetime.utcnow() - timedelta(hours=i)
            # Only 10% meetings
            signal.signal_type = 'meeting_attended' if i % 10 == 0 else 'task_completed'
            signals.append(signal)
        
        patterns = {}
        flags = copilot._identify_trend_flags(signals, patterns)
        
        assert 'reduced_meetings' in flags
    
    def test_identify_trend_flags_low_collaboration(self, copilot):
        """Test low collaboration flag"""
        signals = []
        for i in range(100):
            signal = Mock()
            signal.timestamp = datetime.utcnow() - timedelta(hours=i)
            # Very few collaboration signals
            signal.signal_type = 'task_completed'
            signals.append(signal)
        
        patterns = {}
        flags = copilot._identify_trend_flags(signals, patterns)
        
        assert 'low_collaboration' in flags
    
    # ========================================================================
    # ACHIEVEMENT TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_get_achievements_high_productivity(self, copilot, mock_db):
        """Test high productivity achievement"""
        employee_id = str(uuid.uuid4())
        
        # Mock many task completions
        signals = []
        for i in range(60):
            signal = Mock()
            signal.signal_type = 'task_completed'
            signal.timestamp = datetime.utcnow() - timedelta(days=i // 3)
            signals.append(signal)
        
        # Mock trust scores
        scores = [
            (70.0, datetime.utcnow() - timedelta(days=30)),
            (75.0, datetime.utcnow()),
        ]
        
        mock_db.execute = AsyncMock(side_effect=[
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=signals)))),
            Mock(fetchall=Mock(return_value=scores)),
        ])
        
        achievements = await copilot.get_achievements(employee_id, 30, mock_db)
        
        # Should have high productivity achievement
        assert any(a['type'] == 'productivity' for a in achievements)
    
    @pytest.mark.asyncio
    async def test_get_achievements_collaboration(self, copilot, mock_db):
        """Test collaboration achievement"""
        employee_id = str(uuid.uuid4())
        
        # Mock many collaboration signals
        signals = []
        for i in range(30):
            signal = Mock()
            signal.signal_type = 'meeting_attended' if i % 2 == 0 else 'code_review'
            signal.timestamp = datetime.utcnow() - timedelta(days=i)
            signals.append(signal)
        
        scores = []
        
        mock_db.execute = AsyncMock(side_effect=[
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=signals)))),
            Mock(fetchall=Mock(return_value=scores)),
        ])
        
        achievements = await copilot.get_achievements(employee_id, 30, mock_db)
        
        # Should have collaboration achievement
        assert any(a['type'] == 'collaboration' for a in achievements)
    
    # ========================================================================
    # CHALLENGE IDENTIFICATION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_identify_challenges_late_night_work(self, copilot, mock_db):
        """Test late night work challenge"""
        employee_id = str(uuid.uuid4())
        
        # Mock late night signals
        signals = []
        for i in range(20):
            signal = Mock()
            signal.timestamp = datetime.utcnow().replace(hour=22) - timedelta(days=i)
            signal.signal_type = 'task_completed'
            signals.append(signal)
        
        mock_db.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=signals))))
        )
        
        challenges = await copilot.identify_challenges(employee_id, mock_db)
        
        assert 'late_night_work' in challenges
    
    @pytest.mark.asyncio
    async def test_identify_challenges_weekend_work(self, copilot, mock_db):
        """Test weekend work challenge"""
        employee_id = str(uuid.uuid4())
        
        # Mock weekend signals (Saturday = 5, Sunday = 6)
        signals = []
        base_date = datetime.utcnow()
        # Find next Saturday
        days_until_saturday = (5 - base_date.weekday()) % 7
        saturday = base_date + timedelta(days=days_until_saturday)
        
        for i in range(10):
            signal = Mock()
            signal.timestamp = saturday - timedelta(weeks=i)
            signal.signal_type = 'task_completed'
            signals.append(signal)
        
        mock_db.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=signals))))
        )
        
        challenges = await copilot.identify_challenges(employee_id, mock_db)
        
        assert 'weekend_work' in challenges
    
    @pytest.mark.asyncio
    async def test_identify_challenges_high_meeting_load(self, copilot, mock_db):
        """Test high meeting load challenge"""
        employee_id = str(uuid.uuid4())
        
        # Mock many meeting signals
        signals = []
        for i in range(70):
            signal = Mock()
            signal.timestamp = datetime.utcnow() - timedelta(hours=i)
            signal.signal_type = 'meeting_attended'
            signals.append(signal)
        
        mock_db.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=signals))))
        )
        
        challenges = await copilot.identify_challenges(employee_id, mock_db)
        
        assert 'high_meeting_load' in challenges
    
    # ========================================================================
    # RECOMMENDATION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_peak_hours(self, copilot, mock_db):
        """Test peak hours recommendation"""
        employee_id = str(uuid.uuid4())
        
        trends = {
            'patterns': {'peak_hours': (9, 12)},
            'flags': [],
        }
        challenges = []
        
        recommendations = await copilot.generate_recommendations(
            employee_id, trends, challenges, mock_db
        )
        
        # Should have peak productivity recommendation
        assert any('Peak Productivity' in r['title'] for r in recommendations)
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_wellness(self, copilot, mock_db):
        """Test wellness recommendations"""
        employee_id = str(uuid.uuid4())
        
        trends = {'patterns': {}, 'flags': []}
        challenges = ['late_night_work', 'weekend_work']
        
        recommendations = await copilot.generate_recommendations(
            employee_id, trends, challenges, mock_db
        )
        
        # Should have wellness recommendations
        wellness_recs = [r for r in recommendations if r['category'] == 'wellness']
        assert len(wellness_recs) >= 2
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_priority_sorting(self, copilot, mock_db):
        """Test recommendations are sorted by priority"""
        employee_id = str(uuid.uuid4())
        
        trends = {'patterns': {}, 'flags': []}
        challenges = ['late_night_work', 'high_meeting_load', 'deadline_pressure']
        
        recommendations = await copilot.generate_recommendations(
            employee_id, trends, challenges, mock_db
        )
        
        # High priority should come first
        if len(recommendations) > 1:
            assert recommendations[0]['priority'] in ['high', 'medium']
    
    # ========================================================================
    # SUMMARY GENERATION TESTS
    # ========================================================================
    
    def test_generate_summary_excellent_performance(self, copilot):
        """Test summary for excellent performance"""
        trends = {}
        achievements = [{'type': 'performance', 'impact': 'high'}]
        metrics = {
            'trust_score': {'current': 85.0},
            'activity': {'tasks_30d': 60},
        }
        
        summary = copilot._generate_summary(trends, achievements, metrics)
        
        assert 'excellently' in summary.lower() or 'great' in summary.lower()
        assert '60 tasks' in summary or 'tasks' in summary
    
    def test_generate_summary_good_performance(self, copilot):
        """Test summary for good performance"""
        trends = {}
        achievements = []
        metrics = {
            'trust_score': {'current': 70.0},
            'activity': {'tasks_30d': 30},
        }
        
        summary = copilot._generate_summary(trends, achievements, metrics)
        
        assert 'great' in summary.lower() or 'doing' in summary.lower()
    
    # ========================================================================
    # WELLNESS INSIGHTS TESTS
    # ========================================================================
    
    def test_generate_wellness_insights_excellent(self, copilot):
        """Test wellness insights - excellent"""
        trends = {'flags': []}
        
        wellness = copilot._generate_wellness_insights(trends)
        
        assert wellness['status'] == 'excellent'
        assert wellness['score'] >= 80
    
    def test_generate_wellness_insights_concerning(self, copilot):
        """Test wellness insights - concerning"""
        trends = {
            'flags': ['late_night_work', 'weekend_work', 'long_work_days']
        }
        
        wellness = copilot._generate_wellness_insights(trends)
        
        assert wellness['status'] in ['needs_attention', 'concerning']
        assert wellness['score'] < 60
    
    # ========================================================================
    # FORMAT TESTS
    # ========================================================================
    
    def test_format_achievements(self, copilot):
        """Test achievement formatting"""
        achievements = [
            {'type': 'test', 'impact': 'low'},
            {'type': 'test', 'impact': 'high'},
            {'type': 'test', 'impact': 'medium'},
        ]
        
        formatted = copilot._format_achievements(achievements)
        
        # Should be sorted by impact (high first)
        assert formatted[0]['impact'] == 'high'
        assert formatted[-1]['impact'] == 'low'
    
    def test_format_challenges(self, copilot):
        """Test challenge formatting"""
        challenges = ['late_night_work', 'high_meeting_load']
        
        formatted = copilot._format_challenges(challenges)
        
        assert len(formatted) == 2
        assert all('title' in f for f in formatted)
        assert all('description' in f for f in formatted)
        assert all('icon' in f for f in formatted)


# ========================================================================
# INTEGRATION TESTS
# ========================================================================

class TestEmployeeCopilotIntegration:
    """Integration tests for Employee Copilot"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_insights_generation(self):
        """Test complete insights generation workflow"""
        # This would test the full workflow with real database
        # Placeholder for integration test
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
