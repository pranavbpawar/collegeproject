"""
Burnout Prediction System
Predicts employee burnout risk 4 weeks in advance using multi-factor analysis
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from enum import Enum
import statistics


# ============================================================================
# DATA CLASSES
# ============================================================================

class BurnoutRiskLevel(Enum):
    """Burnout risk levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationPriority(Enum):
    """Recommendation priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BurnoutIndicators:
    """Burnout indicator flags and scores"""
    excessive_hours: bool
    excessive_hours_score: float
    
    low_engagement: bool
    engagement_score: float
    
    productivity_decline: bool
    productivity_score: float
    
    sleep_issues: bool
    sleep_score: float
    
    high_stress: bool
    stress_score: float


@dataclass
class Recommendation:
    """Actionable recommendation"""
    action: str
    details: str
    priority: RecommendationPriority
    category: str
    estimated_impact: str


@dataclass
class BurnoutPrediction:
    """Complete burnout prediction result"""
    employee_id: str
    burnout_score: float  # 0-100
    risk_level: BurnoutRiskLevel
    indicators: BurnoutIndicators
    recommendations: List[Recommendation]
    prediction_date: datetime  # 4 weeks from now
    confidence: float  # 0-1
    calculated_at: datetime


# ============================================================================
# BURNOUT PREDICTOR
# ============================================================================

class BurnoutPredictor:
    """
    Burnout Prediction System
    
    Predicts employee burnout risk 4 weeks in advance using:
    - Excessive work hours
    - Low engagement
    - Productivity decline
    - Sleep quality issues
    - High stress indicators
    
    Provides actionable recommendations for intervention.
    """
    
    # Prediction window
    PREDICTION_WINDOW_DAYS = 28  # 4 weeks
    ANALYSIS_WINDOW_DAYS = 28    # Analyze last 4 weeks
    
    # Work hours thresholds
    EXCESSIVE_HOURS_THRESHOLD = 50  # hours/week
    LATE_NIGHT_HOUR = 21  # 9 PM
    EARLY_MORNING_HOUR = 6  # 6 AM
    VERY_LATE_HOUR = 23  # 11 PM
    
    # Engagement thresholds
    ENGAGEMENT_DECLINE_THRESHOLD = 0.20  # 20% decline
    
    # Productivity thresholds
    PRODUCTIVITY_DECLINE_THRESHOLD = 0.15  # 15% decline
    
    # Stress thresholds
    STRESS_INCREASE_THRESHOLD = 0.25  # 25% increase
    
    # Scoring weights
    INDICATOR_WEIGHTS = {
        'excessive_hours': 0.25,
        'low_engagement': 0.20,
        'productivity_decline': 0.20,
        'sleep_issues': 0.20,
        'high_stress': 0.15
    }
    
    def __init__(self, db_connection=None):
        """
        Initialize Burnout Predictor
        
        Args:
            db_connection: Database connection for fetching signals
        """
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
    
    # ========================================================================
    # MAIN PREDICTION
    # ========================================================================
    
    async def predict_burnout(
        self,
        employee_id: str,
        window_days: int = None
    ) -> BurnoutPrediction:
        """
        Predict burnout risk for employee
        
        Args:
            employee_id: Employee identifier
            window_days: Analysis window (default: 28 days)
        
        Returns:
            BurnoutPrediction with risk score and recommendations
        """
        if window_days is None:
            window_days = self.ANALYSIS_WINDOW_DAYS
        
        # Get signals for analysis
        signals = await self.get_signals(employee_id, window_days)
        
        if not signals:
            self.logger.warning(f"No signals found for employee {employee_id}")
            return self._create_default_prediction(employee_id)
        
        # Calculate indicators
        indicators = await self.calculate_indicators(employee_id, signals)
        
        # Calculate burnout score
        burnout_score = self.calculate_burnout_score(indicators)
        
        # Determine risk level
        risk_level = self.determine_risk_level(burnout_score)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(indicators, risk_level)
        
        # Calculate confidence
        confidence = self.calculate_confidence(signals, indicators)
        
        return BurnoutPrediction(
            employee_id=employee_id,
            burnout_score=burnout_score,
            risk_level=risk_level,
            indicators=indicators,
            recommendations=recommendations,
            prediction_date=datetime.utcnow() + timedelta(days=self.PREDICTION_WINDOW_DAYS),
            confidence=confidence,
            calculated_at=datetime.utcnow()
        )
    
    # ========================================================================
    # INDICATOR CALCULATIONS
    # ========================================================================
    
    async def calculate_indicators(
        self,
        employee_id: str,
        signals: Dict[str, Any]
    ) -> BurnoutIndicators:
        """
        Calculate all burnout indicators
        
        Args:
            employee_id: Employee identifier
            signals: Signal data
        
        Returns:
            BurnoutIndicators with all flags and scores
        """
        # Calculate each indicator
        excessive_hours, hours_score = await self.calc_work_hours(employee_id, signals)
        low_engagement, engagement_score = await self.calc_engagement_trend(employee_id, signals)
        productivity_decline, productivity_score = await self.calc_productivity_trend(employee_id, signals)
        sleep_issues, sleep_score = await self.calc_sleep_quality(employee_id, signals)
        high_stress, stress_score = await self.calc_stress_indicators(employee_id, signals)
        
        return BurnoutIndicators(
            excessive_hours=excessive_hours,
            excessive_hours_score=hours_score,
            low_engagement=low_engagement,
            engagement_score=engagement_score,
            productivity_decline=productivity_decline,
            productivity_score=productivity_score,
            sleep_issues=sleep_issues,
            sleep_score=sleep_score,
            high_stress=high_stress,
            stress_score=stress_score
        )
    
    async def calc_work_hours(
        self,
        employee_id: str,
        signals: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Calculate excessive work hours indicator
        
        Checks for:
        - >50 hours/week consistently
        - Late night work (after 9 PM)
        - Weekend work patterns
        - Declining vacation usage
        
        Returns:
            Tuple of (is_excessive, score)
        """
        score = 0.0
        
        # Get work hours data
        weekly_hours = signals.get('weekly_hours', [])
        late_night_count = signals.get('late_night_work_count', 0)
        weekend_work_count = signals.get('weekend_work_count', 0)
        vacation_days_used = signals.get('vacation_days_used', 0)
        vacation_days_baseline = signals.get('vacation_days_baseline', 10)
        
        # Check weekly hours (40 points max)
        if weekly_hours:
            avg_hours = statistics.mean(weekly_hours)
            if avg_hours > self.EXCESSIVE_HOURS_THRESHOLD:
                score += 40.0
            elif avg_hours > 45:
                score += 30.0
            elif avg_hours > 42:
                score += 20.0
        
        # Check late night work (30 points max)
        if late_night_count > 10:  # >10 late nights in 4 weeks
            score += 30.0
        elif late_night_count > 5:
            score += 20.0
        elif late_night_count > 2:
            score += 10.0
        
        # Check weekend work (20 points max)
        if weekend_work_count > 6:  # >6 weekend days in 4 weeks
            score += 20.0
        elif weekend_work_count > 3:
            score += 10.0
        
        # Check vacation usage (10 points max)
        if vacation_days_baseline > 0:
            vacation_ratio = vacation_days_used / vacation_days_baseline
            if vacation_ratio < 0.3:  # Using <30% of vacation
                score += 10.0
            elif vacation_ratio < 0.5:
                score += 5.0
        
        is_excessive = score > 50.0
        
        return is_excessive, min(100.0, score)
    
    async def calc_engagement_trend(
        self,
        employee_id: str,
        signals: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Calculate low engagement indicator
        
        Checks for:
        - Declining meeting attendance
        - Fewer collaborative interactions
        - Reduced email responsiveness
        - Lower task completion
        
        Returns:
            Tuple of (is_low_engagement, score)
        """
        score = 0.0
        
        # Get engagement data
        meeting_attendance_trend = signals.get('meeting_attendance_trend', 0.0)
        collaboration_trend = signals.get('collaboration_trend', 0.0)
        email_response_trend = signals.get('email_response_trend', 0.0)
        task_completion_trend = signals.get('task_completion_trend', 0.0)
        
        # Check meeting attendance (25 points max)
        if meeting_attendance_trend < -self.ENGAGEMENT_DECLINE_THRESHOLD:
            score += 25.0
        elif meeting_attendance_trend < -0.10:
            score += 15.0
        
        # Check collaboration (25 points max)
        if collaboration_trend < -self.ENGAGEMENT_DECLINE_THRESHOLD:
            score += 25.0
        elif collaboration_trend < -0.10:
            score += 15.0
        
        # Check email responsiveness (25 points max)
        if email_response_trend < -self.ENGAGEMENT_DECLINE_THRESHOLD:
            score += 25.0
        elif email_response_trend < -0.10:
            score += 15.0
        
        # Check task completion (25 points max)
        if task_completion_trend < -self.ENGAGEMENT_DECLINE_THRESHOLD:
            score += 25.0
        elif task_completion_trend < -0.10:
            score += 15.0
        
        is_low = score > 50.0
        
        return is_low, min(100.0, score)
    
    async def calc_productivity_trend(
        self,
        employee_id: str,
        signals: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Calculate productivity decline indicator
        
        Checks for:
        - Task completion rate declining
        - Quality declining
        - Deadline misses increasing
        - Rework ratio high
        
        Returns:
            Tuple of (is_declining, score)
        """
        score = 0.0
        
        # Get productivity data
        completion_rate_trend = signals.get('completion_rate_trend', 0.0)
        quality_trend = signals.get('quality_trend', 0.0)
        deadline_miss_trend = signals.get('deadline_miss_trend', 0.0)
        rework_ratio = signals.get('rework_ratio', 0.0)
        
        # Check completion rate (30 points max)
        if completion_rate_trend < -self.PRODUCTIVITY_DECLINE_THRESHOLD:
            score += 30.0
        elif completion_rate_trend < -0.10:
            score += 20.0
        
        # Check quality (30 points max)
        if quality_trend < -self.PRODUCTIVITY_DECLINE_THRESHOLD:
            score += 30.0
        elif quality_trend < -0.10:
            score += 20.0
        
        # Check deadline misses (25 points max)
        if deadline_miss_trend > self.PRODUCTIVITY_DECLINE_THRESHOLD:
            score += 25.0
        elif deadline_miss_trend > 0.10:
            score += 15.0
        
        # Check rework ratio (15 points max)
        if rework_ratio > 0.30:  # >30% rework
            score += 15.0
        elif rework_ratio > 0.20:
            score += 10.0
        
        is_declining = score > 50.0
        
        return is_declining, min(100.0, score)
    
    async def calc_sleep_quality(
        self,
        employee_id: str,
        signals: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Calculate sleep quality issues indicator
        
        Checks for:
        - Late nights (work signals after 11 PM)
        - Early mornings (before 6 AM)
        - Irregular sleep patterns
        
        Returns:
            Tuple of (has_issues, score)
        """
        score = 0.0
        
        # Get sleep data
        very_late_night_count = signals.get('very_late_night_count', 0)  # After 11 PM
        early_morning_count = signals.get('early_morning_count', 0)  # Before 6 AM
        sleep_pattern_irregularity = signals.get('sleep_pattern_irregularity', 0.0)
        
        # Check very late nights (40 points max)
        if very_late_night_count > 10:  # >10 nights after 11 PM
            score += 40.0
        elif very_late_night_count > 5:
            score += 30.0
        elif very_late_night_count > 2:
            score += 20.0
        
        # Check early mornings (30 points max)
        if early_morning_count > 10:
            score += 30.0
        elif early_morning_count > 5:
            score += 20.0
        elif early_morning_count > 2:
            score += 10.0
        
        # Check pattern irregularity (30 points max)
        # Irregularity: 0.0 = regular, 1.0 = very irregular
        if sleep_pattern_irregularity > 0.7:
            score += 30.0
        elif sleep_pattern_irregularity > 0.5:
            score += 20.0
        elif sleep_pattern_irregularity > 0.3:
            score += 10.0
        
        has_issues = score > 50.0
        
        return has_issues, min(100.0, score)
    
    async def calc_stress_indicators(
        self,
        employee_id: str,
        signals: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Calculate high stress indicator
        
        Checks for:
        - Increased email urgency markers
        - Sentiment declining negative
        - Anomaly detections increasing
        - Context switching high
        
        Returns:
            Tuple of (is_high_stress, score)
        """
        score = 0.0
        
        # Get stress data
        urgency_trend = signals.get('urgency_trend', 0.0)
        sentiment_trend = signals.get('sentiment_trend', 0.0)
        anomaly_trend = signals.get('anomaly_trend', 0.0)
        context_switches = signals.get('context_switches_per_day', 0)
        
        # Check urgency increase (30 points max)
        if urgency_trend > self.STRESS_INCREASE_THRESHOLD:
            score += 30.0
        elif urgency_trend > 0.15:
            score += 20.0
        
        # Check sentiment decline (30 points max)
        if sentiment_trend < -0.20:
            score += 30.0
        elif sentiment_trend < -0.10:
            score += 20.0
        
        # Check anomaly increase (25 points max)
        if anomaly_trend > self.STRESS_INCREASE_THRESHOLD:
            score += 25.0
        elif anomaly_trend > 0.15:
            score += 15.0
        
        # Check context switching (15 points max)
        if context_switches > 50:  # >50 switches per day
            score += 15.0
        elif context_switches > 30:
            score += 10.0
        
        is_high = score > 50.0
        
        return is_high, min(100.0, score)
    
    # ========================================================================
    # SCORING
    # ========================================================================
    
    def calculate_burnout_score(self, indicators: BurnoutIndicators) -> float:
        """
        Calculate overall burnout risk score (0-100)
        
        Uses weighted combination of indicator scores
        
        Args:
            indicators: BurnoutIndicators
        
        Returns:
            Burnout score (0-100)
        """
        score = (
            indicators.excessive_hours_score * self.INDICATOR_WEIGHTS['excessive_hours'] +
            indicators.engagement_score * self.INDICATOR_WEIGHTS['low_engagement'] +
            indicators.productivity_score * self.INDICATOR_WEIGHTS['productivity_decline'] +
            indicators.sleep_score * self.INDICATOR_WEIGHTS['sleep_issues'] +
            indicators.stress_score * self.INDICATOR_WEIGHTS['high_stress']
        )
        
        return min(100.0, max(0.0, score))
    
    def determine_risk_level(self, burnout_score: float) -> BurnoutRiskLevel:
        """
        Determine risk level from burnout score
        
        Args:
            burnout_score: Burnout score (0-100)
        
        Returns:
            BurnoutRiskLevel
        """
        if burnout_score >= 75:
            return BurnoutRiskLevel.CRITICAL
        elif burnout_score >= 50:
            return BurnoutRiskLevel.HIGH
        elif burnout_score >= 25:
            return BurnoutRiskLevel.MODERATE
        else:
            return BurnoutRiskLevel.LOW
    
    def calculate_confidence(
        self,
        signals: Dict[str, Any],
        indicators: BurnoutIndicators
    ) -> float:
        """
        Calculate prediction confidence (0-1)
        
        Based on:
        - Data completeness
        - Signal consistency
        - Indicator agreement
        
        Args:
            signals: Signal data
            indicators: BurnoutIndicators
        
        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence
        
        # Data completeness (up to +0.3)
        required_signals = [
            'weekly_hours', 'meeting_attendance_trend',
            'completion_rate_trend', 'sentiment_trend'
        ]
        completeness = sum(1 for s in required_signals if s in signals) / len(required_signals)
        confidence += completeness * 0.3
        
        # Indicator agreement (up to +0.2)
        indicators_triggered = sum([
            indicators.excessive_hours,
            indicators.low_engagement,
            indicators.productivity_decline,
            indicators.sleep_issues,
            indicators.high_stress
        ])
        
        if indicators_triggered >= 3:
            confidence += 0.2  # High agreement
        elif indicators_triggered >= 2:
            confidence += 0.1  # Moderate agreement
        
        return min(1.0, max(0.0, confidence))
    
    # ========================================================================
    # RECOMMENDATIONS
    # ========================================================================
    
    def generate_recommendations(
        self,
        indicators: BurnoutIndicators,
        risk_level: BurnoutRiskLevel
    ) -> List[Recommendation]:
        """
        Generate personalized recommendations
        
        Args:
            indicators: BurnoutIndicators
            risk_level: BurnoutRiskLevel
        
        Returns:
            List of Recommendations
        """
        recommendations = []
        
        # Excessive hours recommendations
        if indicators.excessive_hours:
            priority = RecommendationPriority.URGENT if risk_level == BurnoutRiskLevel.CRITICAL else RecommendationPriority.HIGH
            recommendations.append(Recommendation(
                action="Reduce work hours immediately",
                details="Delegate tasks to team members, decline non-essential meetings, and set strict work hour boundaries",
                priority=priority,
                category="work_hours",
                estimated_impact="High - Can reduce burnout risk by 25%"
            ))
        
        # Low engagement recommendations
        if indicators.low_engagement:
            priority = RecommendationPriority.HIGH if risk_level in [BurnoutRiskLevel.CRITICAL, BurnoutRiskLevel.HIGH] else RecommendationPriority.MEDIUM
            recommendations.append(Recommendation(
                action="Take time off",
                details="Schedule vacation or personal days within the next 2 weeks to recharge",
                priority=priority,
                category="engagement",
                estimated_impact="High - Can reduce burnout risk by 20%"
            ))
        
        # Productivity decline recommendations
        if indicators.productivity_decline:
            recommendations.append(Recommendation(
                action="Simplify workload",
                details="Focus on high-priority tasks, eliminate low-value work, and request deadline extensions if needed",
                priority=RecommendationPriority.HIGH,
                category="productivity",
                estimated_impact="Medium - Can reduce burnout risk by 15%"
            ))
        
        # Sleep issues recommendations
        if indicators.sleep_issues:
            priority = RecommendationPriority.HIGH if indicators.sleep_score > 70 else RecommendationPriority.MEDIUM
            recommendations.append(Recommendation(
                action="Improve sleep schedule",
                details="Stop work by 8 PM, establish consistent sleep/wake times, and avoid late-night emails",
                priority=priority,
                category="sleep",
                estimated_impact="Medium - Can reduce burnout risk by 20%"
            ))
        
        # High stress recommendations
        if indicators.high_stress:
            recommendations.append(Recommendation(
                action="Manage stress levels",
                details="Consider wellness program, practice mindfulness, and schedule regular breaks throughout the day",
                priority=RecommendationPriority.MEDIUM,
                category="stress",
                estimated_impact="Medium - Can reduce burnout risk by 15%"
            ))
        
        # General recommendations based on risk level
        if risk_level == BurnoutRiskLevel.CRITICAL:
            recommendations.insert(0, Recommendation(
                action="URGENT: Immediate intervention required",
                details="Schedule meeting with manager and HR to discuss workload and support options",
                priority=RecommendationPriority.URGENT,
                category="intervention",
                estimated_impact="Critical - Immediate action needed"
            ))
        
        # Sort by priority
        priority_order = {
            RecommendationPriority.URGENT: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])
        
        return recommendations
    
    # ========================================================================
    # DATA FETCHING
    # ========================================================================
    
    async def get_signals(
        self,
        employee_id: str,
        days: int
    ) -> Dict[str, Any]:
        """
        Fetch signals for burnout analysis
        
        Args:
            employee_id: Employee identifier
            days: Number of days to analyze
        
        Returns:
            Dictionary of signal data
        """
        if not self.db:
            # Return mock data for testing
            return self._get_mock_signals()
        
        try:
            # Fetch from database
            query = """
                SELECT
                    -- Work hours
                    ARRAY_AGG(DISTINCT weekly_hours) as weekly_hours,
                    COUNT(CASE WHEN hour_of_day >= 21 THEN 1 END) as late_night_work_count,
                    COUNT(CASE WHEN day_of_week IN (5, 6) THEN 1 END) as weekend_work_count,
                    
                    -- Engagement trends (would need actual calculation)
                    0.0 as meeting_attendance_trend,
                    0.0 as collaboration_trend,
                    0.0 as email_response_trend,
                    0.0 as task_completion_trend,
                    
                    -- Productivity trends
                    0.0 as completion_rate_trend,
                    0.0 as quality_trend,
                    0.0 as deadline_miss_trend,
                    0.0 as rework_ratio,
                    
                    -- Sleep quality
                    COUNT(CASE WHEN hour_of_day >= 23 THEN 1 END) as very_late_night_count,
                    COUNT(CASE WHEN hour_of_day < 6 THEN 1 END) as early_morning_count,
                    0.0 as sleep_pattern_irregularity,
                    
                    -- Stress indicators
                    0.0 as urgency_trend,
                    0.0 as sentiment_trend,
                    0.0 as anomaly_trend,
                    0 as context_switches_per_day
                    
                FROM signals
                WHERE employee_id = $1
                    AND timestamp > NOW() - ($2 || ' days')::INTERVAL
            """
            
            result = await self.db.fetchrow(query, employee_id, days)
            return dict(result) if result else {}
            
        except Exception as e:
            self.logger.error(f"Error fetching signals: {e}")
            return {}
    
    def _get_mock_signals(self) -> Dict[str, Any]:
        """Get mock signals for testing"""
        return {
            'weekly_hours': [52, 51, 53, 50],
            'late_night_work_count': 12,
            'weekend_work_count': 7,
            'vacation_days_used': 2,
            'vacation_days_baseline': 10,
            'meeting_attendance_trend': -0.25,
            'collaboration_trend': -0.18,
            'email_response_trend': -0.22,
            'task_completion_trend': -0.15,
            'completion_rate_trend': -0.20,
            'quality_trend': -0.18,
            'deadline_miss_trend': 0.30,
            'rework_ratio': 0.35,
            'very_late_night_count': 15,
            'early_morning_count': 8,
            'sleep_pattern_irregularity': 0.75,
            'urgency_trend': 0.30,
            'sentiment_trend': -0.25,
            'anomaly_trend': 0.28,
            'context_switches_per_day': 55
        }
    
    def _create_default_prediction(self, employee_id: str) -> BurnoutPrediction:
        """Create default prediction when no data available"""
        return BurnoutPrediction(
            employee_id=employee_id,
            burnout_score=0.0,
            risk_level=BurnoutRiskLevel.LOW,
            indicators=BurnoutIndicators(
                excessive_hours=False,
                excessive_hours_score=0.0,
                low_engagement=False,
                engagement_score=0.0,
                productivity_decline=False,
                productivity_score=0.0,
                sleep_issues=False,
                sleep_score=0.0,
                high_stress=False,
                stress_score=0.0
            ),
            recommendations=[],
            prediction_date=datetime.utcnow() + timedelta(days=self.PREDICTION_WINDOW_DAYS),
            confidence=0.0,
            calculated_at=datetime.utcnow()
        )
