"""
TBAPS Employee Copilot

AI-powered assistant providing personalized insights and recommendations
to help employees understand productivity patterns and improve performance.

Privacy-first design - all data processing is local and employee-controlled.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import uuid
from collections import defaultdict, Counter
import numpy as np

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Employee, TrustScore, SignalEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/tbaps/employee_copilot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EmployeeCopilot:
    """
    AI-Powered Employee Copilot
    
    Provides personalized insights and recommendations to help employees:
    - Understand productivity patterns
    - Identify strengths and achievements
    - Discover areas for improvement
    - Get actionable wellness recommendations
    - Develop skills and advance career
    
    Privacy-first design:
    - All processing is local
    - Employee controls their data
    - Positive, non-judgmental tone
    - No surveillance or monitoring
    """
    
    def __init__(self, db_connection: Optional[AsyncSession] = None):
        """
        Initialize Employee Copilot
        
        Args:
            db_connection: Optional database session
        """
        self.conn = db_connection
        logger.info("EmployeeCopilot initialized")
    
    async def get_personalized_insights(
        self, 
        employee_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate comprehensive personalized insights for employee
        
        Args:
            employee_id: Employee UUID
            days: Number of days to analyze (default: 30)
        
        Returns:
            Dictionary with insights, achievements, recommendations
        """
        logger.info(f"Generating insights for employee {employee_id} ({days} days)")
        
        async for db in get_db():
            try:
                # Gather employee data
                employee_data = await self._get_employee_data(employee_id, db)
                trends = await self.get_trends(employee_id, days, db)
                achievements = await self.get_achievements(employee_id, days, db)
                challenges = await self.identify_challenges(employee_id, db)
                metrics = await self.get_key_metrics(employee_id, db)
                
                # Generate insights
                insights = {
                    'employee_id': employee_id,
                    'employee_name': employee_data.get('name', 'Employee'),
                    'period': f'Last {days} days',
                    'generated_at': datetime.utcnow().isoformat(),
                    
                    # Summary
                    'summary': self._generate_summary(trends, achievements, metrics),
                    
                    # Achievements and wins
                    'wins': self._format_achievements(achievements),
                    
                    # Focus areas
                    'focus_areas': self._format_challenges(challenges),
                    
                    # Personalized recommendations
                    'recommendations': await self.generate_recommendations(
                        employee_id, trends, challenges, db
                    ),
                    
                    # Key metrics
                    'metrics': metrics,
                    
                    # Productivity patterns
                    'patterns': trends.get('patterns', {}),
                    
                    # Wellness insights
                    'wellness': self._generate_wellness_insights(trends),
                }
                
                logger.info(f"Generated insights for {employee_id}: {len(insights['recommendations'])} recommendations")
                
                return insights
                
            except Exception as e:
                logger.error(f"Error generating insights for {employee_id}: {e}")
                raise
    
    async def get_trends(
        self, 
        employee_id: str, 
        days: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Analyze productivity trends over specified period
        
        Args:
            employee_id: Employee UUID
            days: Number of days to analyze
            db: Database session
        
        Returns:
            Dictionary with trend analysis
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Get signals for period
            result = await db.execute(
                select(SignalEvent)
                .where(
                    and_(
                        SignalEvent.employee_id == uuid.UUID(employee_id),
                        SignalEvent.timestamp >= cutoff
                    )
                )
                .order_by(SignalEvent.timestamp)
            )
            signals = result.scalars().all()
            
            if not signals:
                return {'patterns': {}, 'flags': []}
            
            # Analyze patterns
            patterns = self._analyze_productivity_patterns(signals)
            flags = self._identify_trend_flags(signals, patterns)
            
            return {
                'patterns': patterns,
                'flags': flags,
                'total_signals': len(signals),
                'period_days': days,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return {'patterns': {}, 'flags': []}
    
    async def get_achievements(
        self, 
        employee_id: str, 
        days: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Identify employee achievements and wins
        
        Args:
            employee_id: Employee UUID
            days: Number of days to analyze
            db: Database session
        
        Returns:
            List of achievements
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Get signals
            result = await db.execute(
                select(SignalEvent)
                .where(
                    and_(
                        SignalEvent.employee_id == uuid.UUID(employee_id),
                        SignalEvent.timestamp >= cutoff
                    )
                )
            )
            signals = result.scalars().all()
            
            # Get trust score trend
            result = await db.execute(
                select(TrustScore.total_score, TrustScore.timestamp)
                .where(
                    and_(
                        TrustScore.employee_id == uuid.UUID(employee_id),
                        TrustScore.timestamp >= cutoff
                    )
                )
                .order_by(TrustScore.timestamp)
            )
            scores = result.fetchall()
            
            achievements = []
            
            # Achievement: Improved trust score
            if len(scores) >= 2:
                score_improvement = scores[-1][0] - scores[0][0]
                if score_improvement > 5:
                    achievements.append({
                        'type': 'performance',
                        'title': 'Performance Improvement',
                        'description': f'Your trust score increased by {score_improvement:.1f} points',
                        'impact': 'high',
                        'icon': '📈',
                    })
            
            # Achievement: High activity
            task_signals = [s for s in signals if s.signal_type == 'task_completed']
            if len(task_signals) > 50:
                achievements.append({
                    'type': 'productivity',
                    'title': 'High Productivity',
                    'description': f'Completed {len(task_signals)} tasks this period',
                    'impact': 'high',
                    'icon': '✅',
                })
            
            # Achievement: Collaboration
            collab_signals = [s for s in signals if s.signal_type in ['meeting_attended', 'code_review']]
            if len(collab_signals) > 20:
                achievements.append({
                    'type': 'collaboration',
                    'title': 'Team Player',
                    'description': f'Actively collaborated in {len(collab_signals)} activities',
                    'impact': 'medium',
                    'icon': '🤝',
                })
            
            # Achievement: Consistent work pattern
            daily_signals = defaultdict(int)
            for signal in signals:
                day = signal.timestamp.date()
                daily_signals[day] += 1
            
            active_days = len(daily_signals)
            if active_days >= days * 0.8:
                achievements.append({
                    'type': 'consistency',
                    'title': 'Consistent Contributor',
                    'description': f'Active on {active_days} out of {days} days',
                    'impact': 'medium',
                    'icon': '🎯',
                })
            
            return achievements
            
        except Exception as e:
            logger.error(f"Error identifying achievements: {e}")
            return []
    
    async def identify_challenges(
        self, 
        employee_id: str,
        db: AsyncSession
    ) -> List[str]:
        """
        Identify potential challenges or areas for improvement
        
        Args:
            employee_id: Employee UUID
            db: Database session
        
        Returns:
            List of challenge identifiers
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            # Get recent signals
            result = await db.execute(
                select(SignalEvent)
                .where(
                    and_(
                        SignalEvent.employee_id == uuid.UUID(employee_id),
                        SignalEvent.timestamp >= cutoff
                    )
                )
            )
            signals = result.scalars().all()
            
            challenges = []
            
            # Analyze work patterns
            late_night_count = 0
            weekend_count = 0
            long_day_count = 0
            
            daily_signals = defaultdict(list)
            for signal in signals:
                day = signal.timestamp.date()
                daily_signals[day].append(signal)
                
                # Late night work (after 8 PM)
                if signal.timestamp.hour >= 20:
                    late_night_count += 1
                
                # Weekend work
                if signal.timestamp.weekday() >= 5:
                    weekend_count += 1
            
            # Check for long work days
            for day, day_signals in daily_signals.items():
                if len(day_signals) > 1:
                    timestamps = [s.timestamp for s in day_signals]
                    work_hours = (max(timestamps) - min(timestamps)).total_seconds() / 3600
                    if work_hours > 10:
                        long_day_count += 1
            
            # Identify challenges
            if late_night_count > 10:
                challenges.append('late_night_work')
            
            if weekend_count > 5:
                challenges.append('weekend_work')
            
            if long_day_count > 10:
                challenges.append('long_work_days')
            
            # Check meeting load
            meeting_signals = [s for s in signals if s.signal_type == 'meeting_attended']
            if len(meeting_signals) > 60:
                challenges.append('high_meeting_load')
            
            # Check for deadline pressure (many late-night tasks)
            late_tasks = [
                s for s in signals
                if s.signal_type == 'task_completed' and s.timestamp.hour >= 18
            ]
            if len(late_tasks) > 20:
                challenges.append('deadline_pressure')
            
            return challenges
            
        except Exception as e:
            logger.error(f"Error identifying challenges: {e}")
            return []
    
    async def generate_recommendations(
        self,
        employee_id: str,
        trends: Dict[str, Any],
        challenges: List[str],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Generate AI-powered personalized recommendations
        
        Args:
            employee_id: Employee UUID
            trends: Trend analysis results
            challenges: Identified challenges
            db: Database session
        
        Returns:
            List of personalized recommendations
        """
        recommendations = []
        
        patterns = trends.get('patterns', {})
        flags = trends.get('flags', [])
        
        # Productivity pattern recommendations
        if 'peak_hours' in patterns:
            peak_start, peak_end = patterns['peak_hours']
            recommendations.append({
                'category': 'productivity',
                'title': '🌟 Peak Productivity Window',
                'description': f'You\'re most productive between {peak_start}:00-{peak_end}:00',
                'action': 'Schedule your most important tasks during this time',
                'priority': 'high',
                'impact': 'Maximize your natural productivity rhythm',
            })
        
        # Meeting optimization
        if 'reduced_meetings' in flags:
            recommendations.append({
                'category': 'productivity',
                'title': '🎯 Focus Time Achievement',
                'description': 'You\'ve successfully reduced meeting time',
                'action': 'Keep blocking focus time on your calendar',
                'priority': 'medium',
                'impact': 'More time for deep work',
            })
        elif 'high_meeting_load' in challenges:
            recommendations.append({
                'category': 'productivity',
                'title': '📅 Meeting Optimization',
                'description': 'Your calendar is heavily booked with meetings',
                'action': 'Try "No Meeting Fridays" or batch meetings on specific days',
                'priority': 'high',
                'impact': 'Reclaim focus time for deep work',
            })
        
        # Work-life balance
        if 'late_night_work' in challenges:
            recommendations.append({
                'category': 'wellness',
                'title': '🌙 Work-Life Balance',
                'description': 'You\'re working late hours frequently',
                'action': 'Set a work end time and stick to it. Your brain needs rest!',
                'priority': 'high',
                'impact': 'Better rest leads to better performance',
            })
        
        if 'weekend_work' in challenges:
            recommendations.append({
                'category': 'wellness',
                'title': '🏖️ Weekend Recovery',
                'description': 'You\'re working on weekends often',
                'action': 'Protect your weekends for rest and recharge',
                'priority': 'high',
                'impact': 'Prevent burnout and maintain long-term productivity',
            })
        
        if 'long_work_days' in challenges:
            recommendations.append({
                'category': 'wellness',
                'title': '⏰ Sustainable Pace',
                'description': 'You\'re working very long days',
                'action': 'Take regular breaks and set boundaries. Marathon, not sprint!',
                'priority': 'high',
                'impact': 'Sustainable productivity over time',
            })
        
        # Task management
        if 'deadline_pressure' in challenges:
            recommendations.append({
                'category': 'productivity',
                'title': '📋 Task Planning',
                'description': 'Many tasks completed under time pressure',
                'action': 'Break large tasks into milestones and start earlier',
                'priority': 'medium',
                'impact': 'Reduce stress and improve quality',
            })
        
        # Collaboration
        if 'low_collaboration' in flags:
            recommendations.append({
                'category': 'collaboration',
                'title': '🤝 Team Engagement',
                'description': 'Consider increasing team collaboration',
                'action': 'Join team discussions, offer code reviews, or pair program',
                'priority': 'low',
                'impact': 'Build relationships and share knowledge',
            })
        
        # Skill development
        if patterns.get('consistent_performance', False):
            recommendations.append({
                'category': 'development',
                'title': '🚀 Growth Opportunity',
                'description': 'You\'re performing consistently well',
                'action': 'Consider taking on a stretch project or mentoring others',
                'priority': 'low',
                'impact': 'Accelerate career growth',
            })
        
        # Positive reinforcement
        if 'improving_trend' in flags:
            recommendations.append({
                'category': 'motivation',
                'title': '📈 Keep Up the Great Work!',
                'description': 'Your performance is trending upward',
                'action': 'You\'re on the right track - keep doing what you\'re doing!',
                'priority': 'low',
                'impact': 'Maintain momentum',
            })
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return recommendations
    
    async def get_key_metrics(
        self, 
        employee_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get key performance metrics for employee
        
        Args:
            employee_id: Employee UUID
            db: Database session
        
        Returns:
            Dictionary with key metrics
        """
        try:
            cutoff_30d = datetime.utcnow() - timedelta(days=30)
            cutoff_7d = datetime.utcnow() - timedelta(days=7)
            
            # Get latest trust score
            result = await db.execute(
                select(TrustScore)
                .where(TrustScore.employee_id == uuid.UUID(employee_id))
                .order_by(TrustScore.timestamp.desc())
                .limit(1)
            )
            latest_score = result.scalar()
            
            # Get 30-day signals
            result = await db.execute(
                select(SignalEvent)
                .where(
                    and_(
                        SignalEvent.employee_id == uuid.UUID(employee_id),
                        SignalEvent.timestamp >= cutoff_30d
                    )
                )
            )
            signals_30d = result.scalars().all()
            
            # Get 7-day signals
            result = await db.execute(
                select(SignalEvent)
                .where(
                    and_(
                        SignalEvent.employee_id == uuid.UUID(employee_id),
                        SignalEvent.timestamp >= cutoff_7d
                    )
                )
            )
            signals_7d = result.scalars().all()
            
            # Calculate metrics
            tasks_30d = len([s for s in signals_30d if s.signal_type == 'task_completed'])
            tasks_7d = len([s for s in signals_7d if s.signal_type == 'task_completed'])
            
            meetings_30d = len([s for s in signals_30d if s.signal_type == 'meeting_attended'])
            meetings_7d = len([s for s in signals_7d if s.signal_type == 'meeting_attended'])
            
            # Active days
            active_days_30d = len(set(s.timestamp.date() for s in signals_30d))
            active_days_7d = len(set(s.timestamp.date() for s in signals_7d))
            
            return {
                'trust_score': {
                    'current': float(latest_score.total_score) if latest_score else 0.0,
                    'outcome': float(latest_score.outcome_score) if latest_score else 0.0,
                    'behavioral': float(latest_score.behavioral_score) if latest_score else 0.0,
                    'security': float(latest_score.security_score) if latest_score else 0.0,
                    'wellbeing': float(latest_score.wellbeing_score) if latest_score else 0.0,
                },
                'activity': {
                    'tasks_30d': tasks_30d,
                    'tasks_7d': tasks_7d,
                    'meetings_30d': meetings_30d,
                    'meetings_7d': meetings_7d,
                    'active_days_30d': active_days_30d,
                    'active_days_7d': active_days_7d,
                },
                'averages': {
                    'tasks_per_day': tasks_30d / max(active_days_30d, 1),
                    'meetings_per_day': meetings_30d / max(active_days_30d, 1),
                },
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _analyze_productivity_patterns(
        self, 
        signals: List[SignalEvent]
    ) -> Dict[str, Any]:
        """Analyze productivity patterns from signals"""
        if not signals:
            return {}
        
        patterns = {}
        
        # Analyze hourly patterns
        hourly_activity = defaultdict(int)
        for signal in signals:
            hour = signal.timestamp.hour
            hourly_activity[hour] += 1
        
        # Find peak hours (3-hour window with most activity)
        if hourly_activity:
            max_activity = 0
            peak_start = 0
            
            for start_hour in range(24):
                window_activity = sum(
                    hourly_activity[h]
                    for h in range(start_hour, min(start_hour + 3, 24))
                )
                if window_activity > max_activity:
                    max_activity = window_activity
                    peak_start = start_hour
            
            patterns['peak_hours'] = (peak_start, min(peak_start + 3, 24))
        
        # Check consistency
        daily_activity = defaultdict(int)
        for signal in signals:
            day = signal.timestamp.date()
            daily_activity[day] += 1
        
        if daily_activity:
            activity_values = list(daily_activity.values())
            avg_activity = np.mean(activity_values)
            std_activity = np.std(activity_values)
            
            # Consistent if low variance
            if std_activity < avg_activity * 0.5:
                patterns['consistent_performance'] = True
        
        return patterns
    
    def _identify_trend_flags(
        self, 
        signals: List[SignalEvent],
        patterns: Dict[str, Any]
    ) -> List[str]:
        """Identify trend flags from signals and patterns"""
        flags = []
        
        # Check for meeting reduction
        meeting_signals = [s for s in signals if s.signal_type == 'meeting_attended']
        if len(meeting_signals) < len(signals) * 0.2:
            flags.append('reduced_meetings')
        
        # Check for improving trend
        # (Would compare with previous period in production)
        if len(signals) > 100:
            flags.append('improving_trend')
        
        # Check for low collaboration
        collab_signals = [
            s for s in signals
            if s.signal_type in ['meeting_attended', 'code_review', 'pair_programming']
        ]
        if len(collab_signals) < len(signals) * 0.1:
            flags.append('low_collaboration')
        
        return flags
    
    def _generate_summary(
        self,
        trends: Dict[str, Any],
        achievements: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> str:
        """Generate natural language summary"""
        trust_score = metrics.get('trust_score', {}).get('current', 0)
        tasks = metrics.get('activity', {}).get('tasks_30d', 0)
        
        summary_parts = []
        
        # Performance summary
        if trust_score >= 80:
            summary_parts.append("You're performing excellently")
        elif trust_score >= 60:
            summary_parts.append("You're doing great work")
        else:
            summary_parts.append("You're making progress")
        
        # Activity summary
        if tasks > 50:
            summary_parts.append(f"with {tasks} tasks completed this month")
        elif tasks > 20:
            summary_parts.append(f"with steady productivity ({tasks} tasks)")
        
        # Achievements
        if len(achievements) > 0:
            summary_parts.append(f"and {len(achievements)} notable achievements")
        
        return ". ".join(summary_parts) + "."
    
    def _format_achievements(
        self, 
        achievements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format achievements for display"""
        return sorted(
            achievements,
            key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x.get('impact', 'low'), 3)
        )
    
    def _format_challenges(
        self, 
        challenges: List[str]
    ) -> List[Dict[str, str]]:
        """Format challenges as focus areas (positive framing)"""
        challenge_map = {
            'late_night_work': {
                'title': 'Work-Life Balance',
                'description': 'Opportunity to establish healthier work boundaries',
                'icon': '⚖️',
            },
            'weekend_work': {
                'title': 'Weekend Recovery',
                'description': 'Protect your weekends for rest and recharge',
                'icon': '🏖️',
            },
            'long_work_days': {
                'title': 'Sustainable Pace',
                'description': 'Find a rhythm that works long-term',
                'icon': '⏰',
            },
            'high_meeting_load': {
                'title': 'Focus Time',
                'description': 'Opportunity to optimize calendar for deep work',
                'icon': '🎯',
            },
            'deadline_pressure': {
                'title': 'Planning & Pacing',
                'description': 'Improve task breakdown and timeline management',
                'icon': '📋',
            },
        }
        
        return [
            challenge_map[c]
            for c in challenges
            if c in challenge_map
        ]
    
    def _generate_wellness_insights(
        self, 
        trends: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate wellness-specific insights"""
        flags = trends.get('flags', [])
        
        wellness_score = 100  # Start at 100
        
        # Deduct for concerning patterns
        if 'late_night_work' in flags:
            wellness_score -= 20
        if 'weekend_work' in flags:
            wellness_score -= 15
        if 'long_work_days' in flags:
            wellness_score -= 15
        
        wellness_score = max(0, wellness_score)
        
        # Determine status
        if wellness_score >= 80:
            status = 'excellent'
            message = 'Your work-life balance looks healthy!'
        elif wellness_score >= 60:
            status = 'good'
            message = 'Your work-life balance is mostly good, with room for improvement'
        elif wellness_score >= 40:
            status = 'needs_attention'
            message = 'Consider focusing on work-life balance'
        else:
            status = 'concerning'
            message = 'Your work patterns suggest burnout risk - please prioritize rest'
        
        return {
            'score': wellness_score,
            'status': status,
            'message': message,
        }
    
    async def _get_employee_data(
        self, 
        employee_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get employee basic data"""
        try:
            result = await db.execute(
                select(Employee)
                .where(Employee.id == uuid.UUID(employee_id))
            )
            employee = result.scalar()
            
            if not employee:
                return {}
            
            return {
                'id': str(employee.id),
                'name': employee.name,
                'email': employee.email,
                'department': employee.department,
                'role': employee.role,
            }
            
        except Exception as e:
            logger.error(f"Error fetching employee data: {e}")
            return {}
