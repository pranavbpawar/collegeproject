"""
Tests for Intervention Engine

Comprehensive test suite for intervention recommendation system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import uuid

from app.services.intervention_engine import InterventionEngine
from app.services.action_templates import ActionTemplates
from app.services.intervention_tracker import (
    InterventionTracker,
    InterventionStatus,
    InterventionOutcome,
)


class TestInterventionEngine:
    """Test InterventionEngine class"""
    
    @pytest.fixture
    def engine(self):
        """Create intervention engine instance"""
        return InterventionEngine()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    # ========================================================================
    # BURNOUT PREDICTION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_predict_burnout_no_signals(self, engine, mock_db):
        """Test burnout prediction with no signals"""
        employee_id = str(uuid.uuid4())
        
        # Mock database to return no signals
        mock_db.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))))
        
        risk = await engine._predict_burnout(employee_id, mock_db)
        
        assert risk == 0.0
    
    @pytest.mark.asyncio
    async def test_predict_burnout_high_risk(self, engine, mock_db):
        """Test burnout prediction with high risk signals"""
        employee_id = str(uuid.uuid4())
        
        # Create mock signals indicating burnout
        mock_signals = []
        for i in range(20):
            signal = Mock()
            signal.timestamp = datetime.utcnow() - timedelta(days=i)
            # Long work hours (early start, late end)
            if i % 2 == 0:
                signal.timestamp = signal.timestamp.replace(hour=8)
            else:
                signal.timestamp = signal.timestamp.replace(hour=22)
            mock_signals.append(signal)
        
        mock_db.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=mock_signals))))
        )
        
        risk = await engine._predict_burnout(employee_id, mock_db)
        
        assert risk > 0.0
    
    # ========================================================================
    # PERFORMANCE TREND TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_performance_trend_improving(self, engine, mock_db):
        """Test performance trend calculation - improving"""
        employee_id = str(uuid.uuid4())
        
        # Mock scores showing improvement
        mock_scores = [
            (60.0, datetime.utcnow() - timedelta(days=50)),
            (65.0, datetime.utcnow() - timedelta(days=40)),
            (70.0, datetime.utcnow() - timedelta(days=30)),
            (75.0, datetime.utcnow() - timedelta(days=20)),
            (80.0, datetime.utcnow() - timedelta(days=10)),
        ]
        
        mock_db.execute = AsyncMock(
            return_value=Mock(fetchall=Mock(return_value=mock_scores))
        )
        
        trend = await engine._get_performance_trend(employee_id, mock_db)
        
        assert trend > 0.0  # Positive trend = improving
    
    @pytest.mark.asyncio
    async def test_performance_trend_declining(self, engine, mock_db):
        """Test performance trend calculation - declining"""
        employee_id = str(uuid.uuid4())
        
        # Mock scores showing decline
        mock_scores = [
            (80.0, datetime.utcnow() - timedelta(days=50)),
            (75.0, datetime.utcnow() - timedelta(days=40)),
            (70.0, datetime.utcnow() - timedelta(days=30)),
            (65.0, datetime.utcnow() - timedelta(days=20)),
            (60.0, datetime.utcnow() - timedelta(days=10)),
        ]
        
        mock_db.execute = AsyncMock(
            return_value=Mock(fetchall=Mock(return_value=mock_scores))
        )
        
        trend = await engine._get_performance_trend(employee_id, mock_db)
        
        assert trend < 0.0  # Negative trend = declining
    
    # ========================================================================
    # ENGAGEMENT CALCULATION TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_calculate_engagement_high(self, engine, mock_db):
        """Test engagement calculation - high engagement"""
        employee_id = str(uuid.uuid4())
        
        # Mock signals showing high engagement
        mock_signals = []
        for i in range(30):
            signal = Mock()
            signal.signal_type = 'task_completed' if i % 2 == 0 else 'code_commit'
            signal.timestamp = datetime.utcnow() - timedelta(days=i)
            mock_signals.append(signal)
        
        mock_db.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=mock_signals))))
        )
        
        engagement = await engine._calculate_engagement(employee_id, mock_db)
        
        assert engagement > 0.5
    
    @pytest.mark.asyncio
    async def test_calculate_engagement_low(self, engine, mock_db):
        """Test engagement calculation - low engagement"""
        employee_id = str(uuid.uuid4())
        
        # Mock signals showing low engagement
        mock_signals = []
        for i in range(30):
            signal = Mock()
            signal.signal_type = 'other_activity'  # Non-engagement signals
            signal.timestamp = datetime.utcnow() - timedelta(days=i)
            mock_signals.append(signal)
        
        mock_db.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=mock_signals))))
        )
        
        engagement = await engine._calculate_engagement(employee_id, mock_db)
        
        assert engagement < 0.5
    
    # ========================================================================
    # INTERVENTION CREATION TESTS
    # ========================================================================
    
    def test_create_critical_burnout_intervention(self, engine):
        """Test critical burnout intervention creation"""
        employee_data = {
            'id': str(uuid.uuid4()),
            'name': 'John Doe',
            'department': 'Engineering',
        }
        burnout_risk = 0.85
        
        intervention = engine._create_critical_burnout_intervention(
            employee_data, burnout_risk
        )
        
        assert intervention['category'] == 'wellness'
        assert intervention['priority'] == 'critical'
        assert intervention['urgency_days'] == 3
        assert 'URGENT' in intervention['actions'][0]
        assert intervention['risk_level'] == burnout_risk
    
    def test_create_performance_intervention(self, engine):
        """Test performance intervention creation"""
        employee_data = {
            'id': str(uuid.uuid4()),
            'name': 'Jane Smith',
            'department': 'Sales',
        }
        performance_trend = -0.15
        
        intervention = engine._create_performance_intervention(
            employee_data, performance_trend
        )
        
        assert intervention['category'] == 'performance'
        assert intervention['priority'] == 'medium'
        assert intervention['urgency_days'] == 14
        assert 'Skills assessment' in intervention['actions'][0]
        assert intervention['performance_trend'] == performance_trend
    
    def test_create_engagement_intervention(self, engine):
        """Test engagement intervention creation"""
        employee_data = {
            'id': str(uuid.uuid4()),
            'name': 'Bob Johnson',
            'department': 'Marketing',
        }
        trust_score = 45.0
        engagement = 0.3
        
        intervention = engine._create_engagement_intervention(
            employee_data, trust_score, engagement
        )
        
        assert intervention['category'] == 'engagement'
        assert intervention['priority'] == 'high'
        assert intervention['urgency_days'] == 7
        assert 'Career development' in intervention['actions'][0]
        assert intervention['trust_score'] == trust_score
        assert intervention['engagement_score'] == engagement
    
    def test_create_development_intervention(self, engine):
        """Test development intervention creation"""
        employee_data = {
            'id': str(uuid.uuid4()),
            'name': 'Alice Williams',
            'department': 'Engineering',
        }
        trust_score = 85.0
        performance_trend = 0.15
        
        intervention = engine._create_development_intervention(
            employee_data, trust_score, performance_trend
        )
        
        assert intervention['category'] == 'development'
        assert intervention['priority'] == 'low'
        assert intervention['urgency_days'] == 30
        assert 'Leadership training' in intervention['actions'][0]
    
    # ========================================================================
    # PRIORITIZATION TESTS
    # ========================================================================
    
    def test_prioritize_interventions(self, engine):
        """Test intervention prioritization"""
        interventions = [
            {'priority': 'low', 'title': 'Low priority'},
            {'priority': 'critical', 'title': 'Critical priority'},
            {'priority': 'medium', 'title': 'Medium priority'},
            {'priority': 'high', 'title': 'High priority'},
        ]
        
        sorted_interventions = engine._prioritize_interventions(interventions)
        
        assert sorted_interventions[0]['priority'] == 'critical'
        assert sorted_interventions[1]['priority'] == 'high'
        assert sorted_interventions[2]['priority'] == 'medium'
        assert sorted_interventions[3]['priority'] == 'low'


class TestActionTemplates:
    """Test ActionTemplates class"""
    
    def test_get_wellness_critical_template(self):
        """Test getting critical wellness template"""
        template = ActionTemplates.get_template('wellness', 'critical')
        
        assert template is not None
        assert template['title'] == 'Critical Burnout Risk - Immediate Intervention'
        assert template['timeline'] == '3 days'
        assert len(template['actions']) == 5
    
    def test_get_performance_template(self):
        """Test getting performance template"""
        template = ActionTemplates.get_template('performance', 'medium')
        
        assert template is not None
        assert 'Performance Support' in template['title']
        assert len(template['actions']) > 0
    
    def test_get_engagement_template(self):
        """Test getting engagement template"""
        template = ActionTemplates.get_template('engagement', 'high')
        
        assert template is not None
        assert 'Engagement' in template['title']
        assert len(template['actions']) > 0
    
    def test_get_development_template(self):
        """Test getting development template"""
        template = ActionTemplates.get_template('development', 'low')
        
        assert template is not None
        assert 'Leadership' in template['title']
        assert len(template['actions']) > 0
    
    def test_get_all_templates(self):
        """Test getting all templates"""
        templates = ActionTemplates.get_all_templates()
        
        assert len(templates) >= 8
        assert 'wellness_critical' in templates
        assert 'performance_support' in templates
        assert 'engagement_retention' in templates
        assert 'development_leadership' in templates


class TestInterventionTracker:
    """Test InterventionTracker class"""
    
    @pytest.fixture
    def tracker(self):
        """Create intervention tracker instance"""
        return InterventionTracker()
    
    def test_calculate_success_score_successful(self, tracker):
        """Test success score calculation - successful outcome"""
        initial_metrics = {'burnout_risk': 0.8}
        final_metrics = {'burnout_risk': 0.3}
        
        score = tracker._calculate_success_score(
            'wellness',
            initial_metrics,
            final_metrics,
            InterventionOutcome.SUCCESSFUL
        )
        
        assert score >= 1.0  # Base 1.0 + improvement bonus
    
    def test_calculate_success_score_not_successful(self, tracker):
        """Test success score calculation - not successful"""
        initial_metrics = {'burnout_risk': 0.8}
        final_metrics = {'burnout_risk': 0.85}
        
        score = tracker._calculate_success_score(
            'wellness',
            initial_metrics,
            final_metrics,
            InterventionOutcome.NOT_SUCCESSFUL
        )
        
        assert score == 0.2  # Base score for not successful
    
    def test_calculate_success_score_performance_improvement(self, tracker):
        """Test success score for performance improvement"""
        initial_metrics = {'performance_trend': -0.15}
        final_metrics = {'performance_trend': 0.10}
        
        score = tracker._calculate_success_score(
            'performance',
            initial_metrics,
            final_metrics,
            InterventionOutcome.SUCCESSFUL
        )
        
        assert score >= 1.0  # Significant improvement
    
    def test_calculate_success_score_engagement_improvement(self, tracker):
        """Test success score for engagement improvement"""
        initial_metrics = {'trust_score': 45.0}
        final_metrics = {'trust_score': 70.0}
        
        score = tracker._calculate_success_score(
            'engagement',
            initial_metrics,
            final_metrics,
            InterventionOutcome.SUCCESSFUL
        )
        
        assert score >= 1.0  # Significant improvement


# ========================================================================
# INTEGRATION TESTS
# ========================================================================

class TestInterventionEngineIntegration:
    """Integration tests for intervention engine"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_intervention_workflow(self):
        """Test complete intervention workflow"""
        # This would test the full workflow:
        # 1. Generate interventions
        # 2. Create tracking records
        # 3. Update status
        # 4. Complete with outcome
        # 5. Calculate analytics
        
        # Placeholder for full integration test
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
