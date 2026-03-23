"""
TBAPS Intervention Engine

Generates personalized intervention recommendations based on predictive signals:
- At-risk employees
- Burnout prevention
- Career development
- Performance improvement
- Team rebalancing

Proactive, data-driven interventions for employee success.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import uuid
import numpy as np
from collections import defaultdict

from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Employee, TrustScore, SignalEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/tbaps/intervention_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InterventionEngine:
    """
    Intervention Recommendation Engine
    
    Analyzes employee data to generate personalized, actionable interventions:
    - Wellness interventions (burnout prevention)
    - Performance interventions (skill development)
    - Engagement interventions (career growth)
    - Development interventions (leadership opportunities)
    - Team interventions (rebalancing, collaboration)
    """
    
    # Intervention categories
    CATEGORIES = {
        'wellness': 'Employee Wellness & Burnout Prevention',
        'performance': 'Performance Improvement',
        'engagement': 'Engagement & Retention',
        'development': 'Career Development',
        'team': 'Team Dynamics & Collaboration',
    }
    
    # Priority levels
    PRIORITIES = {
        'critical': {'urgency_days': 3, 'color': 'red'},
        'high': {'urgency_days': 7, 'color': 'orange'},
        'medium': {'urgency_days': 14, 'color': 'yellow'},
        'low': {'urgency_days': 30, 'color': 'green'},
    }
    
    # Risk thresholds
    THRESHOLDS = {
        'burnout_critical': 0.8,
        'burnout_high': 0.7,
        'burnout_medium': 0.5,
        'trust_low': 50.0,
        'trust_high': 80.0,
        'performance_declining': -0.1,
        'performance_improving': 0.1,
        'engagement_low': 0.4,
        'engagement_high': 0.7,
    }
    
    def __init__(self, db_connection: Optional[AsyncSession] = None):
        """
        Initialize intervention engine
        
        Args:
            db_connection: Optional database session
        """
        self.conn = db_connection
        logger.info("InterventionEngine initialized")
    
    async def recommend_interventions(
        self, 
        employee_id: str,
        include_low_priority: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized intervention recommendations for an employee
        
        Args:
            employee_id: Employee UUID
            include_low_priority: Whether to include low-priority interventions
        
        Returns:
            List of intervention recommendations
        """
        logger.info(f"Generating interventions for employee {employee_id}")
        
        async for db in get_db():
            try:
                # Gather employee data
                trust_score = await self._get_trust_score(employee_id, db)
                burnout_risk = await self._predict_burnout(employee_id, db)
                performance_trend = await self._get_performance_trend(employee_id, db)
                engagement = await self._calculate_engagement(employee_id, db)
                employee_data = await self._get_employee_data(employee_id, db)
                
                interventions = []
                
                # Critical burnout risk
                if burnout_risk >= self.THRESHOLDS['burnout_critical']:
                    interventions.append(
                        self._create_critical_burnout_intervention(employee_data, burnout_risk)
                    )
                
                # High burnout risk
                elif burnout_risk >= self.THRESHOLDS['burnout_high']:
                    interventions.append(
                        self._create_high_burnout_intervention(employee_data, burnout_risk)
                    )
                
                # Medium burnout risk
                elif burnout_risk >= self.THRESHOLDS['burnout_medium']:
                    interventions.append(
                        self._create_medium_burnout_intervention(employee_data, burnout_risk)
                    )
                
                # Declining performance
                if performance_trend < self.THRESHOLDS['performance_declining']:
                    interventions.append(
                        self._create_performance_intervention(employee_data, performance_trend)
                    )
                
                # Low engagement or trust
                if (trust_score < self.THRESHOLDS['trust_low'] or 
                    engagement < self.THRESHOLDS['engagement_low']):
                    interventions.append(
                        self._create_engagement_intervention(
                            employee_data, trust_score, engagement
                        )
                    )
                
                # Strong performer - development opportunities
                if (trust_score > self.THRESHOLDS['trust_high'] and 
                    performance_trend > self.THRESHOLDS['performance_improving']):
                    if include_low_priority:
                        interventions.append(
                            self._create_development_intervention(
                                employee_data, trust_score, performance_trend
                            )
                        )
                
                # Team dynamics issues
                team_issues = await self._detect_team_issues(employee_id, db)
                if team_issues:
                    interventions.append(
                        self._create_team_intervention(employee_data, team_issues)
                    )
                
                # Sort by priority
                interventions = self._prioritize_interventions(interventions)
                
                # Store recommendations
                await self._store_interventions(employee_id, interventions, db)
                
                logger.info(
                    f"Generated {len(interventions)} interventions for {employee_id}"
                )
                
                return interventions
                
            except Exception as e:
                logger.error(f"Error generating interventions for {employee_id}: {e}")
                raise
    
    async def recommend_team_interventions(
        self, 
        team_id: Optional[str] = None,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate team-level intervention recommendations
        
        Args:
            team_id: Optional team identifier
            department: Optional department name
        
        Returns:
            List of team intervention recommendations
        """
        logger.info(f"Generating team interventions for team={team_id}, dept={department}")
        
        async for db in get_db():
            try:
                # Get team members
                team_members = await self._get_team_members(team_id, department, db)
                
                if not team_members:
                    return []
                
                # Analyze team dynamics
                team_burnout = await self._analyze_team_burnout(team_members, db)
                team_performance = await self._analyze_team_performance(team_members, db)
                team_balance = await self._analyze_team_balance(team_members, db)
                
                interventions = []
                
                # High team burnout
                if team_burnout['avg_risk'] > 0.6:
                    interventions.append({
                        'category': 'wellness',
                        'priority': 'high',
                        'scope': 'team',
                        'title': 'Team Wellness Initiative',
                        'description': f'Team showing high burnout risk ({team_burnout["avg_risk"]:.1%})',
                        'actions': [
                            'Schedule team wellness day',
                            'Review team workload distribution',
                            'Implement flexible work arrangements',
                            'Team building activities',
                            'Mental health resources presentation',
                        ],
                        'urgency_days': 7,
                        'affected_employees': len(team_members),
                        'metrics': team_burnout,
                    })
                
                # Performance issues
                if team_performance['declining_count'] > len(team_members) * 0.3:
                    interventions.append({
                        'category': 'performance',
                        'priority': 'medium',
                        'scope': 'team',
                        'title': 'Team Performance Enhancement',
                        'description': f'{team_performance["declining_count"]} team members showing declining performance',
                        'actions': [
                            'Team skills assessment',
                            'Group training sessions',
                            'Process improvement workshop',
                            'Knowledge sharing sessions',
                            'Pair programming/mentoring',
                        ],
                        'urgency_days': 14,
                        'affected_employees': team_performance['declining_count'],
                        'metrics': team_performance,
                    })
                
                # Team imbalance
                if not team_balance['is_balanced']:
                    interventions.append({
                        'category': 'team',
                        'priority': 'medium',
                        'scope': 'team',
                        'title': 'Team Rebalancing',
                        'description': team_balance['issue'],
                        'actions': [
                            'Review workload distribution',
                            'Consider team restructuring',
                            'Cross-training initiatives',
                            'Hire additional resources',
                            'Redistribute responsibilities',
                        ],
                        'urgency_days': 21,
                        'affected_employees': len(team_members),
                        'metrics': team_balance,
                    })
                
                return interventions
                
            except Exception as e:
                logger.error(f"Error generating team interventions: {e}")
                raise
    
    # ========================================================================
    # INTERVENTION CREATORS
    # ========================================================================
    
    def _create_critical_burnout_intervention(
        self, 
        employee_data: Dict[str, Any],
        burnout_risk: float
    ) -> Dict[str, Any]:
        """Create critical burnout intervention"""
        return {
            'category': 'wellness',
            'priority': 'critical',
            'scope': 'individual',
            'title': 'Critical Burnout Risk - Immediate Action Required',
            'description': f'{employee_data["name"]} shows critical burnout risk ({burnout_risk:.1%})',
            'actions': [
                '🚨 URGENT: Schedule immediate 1:1 with manager',
                'Offer immediate time off (3-5 days)',
                'Reduce workload by 50% for 2 weeks',
                'Connect with Employee Assistance Program (EAP)',
                'Weekly check-ins for next month',
                'Consider temporary project reassignment',
            ],
            'urgency_days': 3,
            'risk_level': burnout_risk,
            'employee_id': employee_data['id'],
            'employee_name': employee_data['name'],
            'department': employee_data['department'],
            'created_at': datetime.utcnow(),
        }
    
    def _create_high_burnout_intervention(
        self, 
        employee_data: Dict[str, Any],
        burnout_risk: float
    ) -> Dict[str, Any]:
        """Create high burnout intervention"""
        return {
            'category': 'wellness',
            'priority': 'high',
            'scope': 'individual',
            'title': 'High Burnout Risk - Wellness Support Needed',
            'description': f'{employee_data["name"]} shows high burnout risk ({burnout_risk:.1%})',
            'actions': [
                'Schedule 1:1 with manager within 7 days',
                'Suggest wellness program (yoga, meditation, counseling)',
                'Review and reduce workload by 25%',
                'Encourage use of vacation time',
                'Bi-weekly check-ins for next 2 months',
                'Flexible work arrangements',
            ],
            'urgency_days': 7,
            'risk_level': burnout_risk,
            'employee_id': employee_data['id'],
            'employee_name': employee_data['name'],
            'department': employee_data['department'],
            'created_at': datetime.utcnow(),
        }
    
    def _create_medium_burnout_intervention(
        self, 
        employee_data: Dict[str, Any],
        burnout_risk: float
    ) -> Dict[str, Any]:
        """Create medium burnout intervention"""
        return {
            'category': 'wellness',
            'priority': 'medium',
            'scope': 'individual',
            'title': 'Moderate Burnout Risk - Preventive Action',
            'description': f'{employee_data["name"]} shows moderate burnout risk ({burnout_risk:.1%})',
            'actions': [
                'Schedule wellness check-in with manager',
                'Share wellness resources and programs',
                'Review work-life balance',
                'Encourage regular breaks and time off',
                'Monthly wellness check-ins',
            ],
            'urgency_days': 14,
            'risk_level': burnout_risk,
            'employee_id': employee_data['id'],
            'employee_name': employee_data['name'],
            'department': employee_data['department'],
            'created_at': datetime.utcnow(),
        }
    
    def _create_performance_intervention(
        self, 
        employee_data: Dict[str, Any],
        performance_trend: float
    ) -> Dict[str, Any]:
        """Create performance improvement intervention"""
        return {
            'category': 'performance',
            'priority': 'medium',
            'scope': 'individual',
            'title': 'Performance Support & Development',
            'description': f'{employee_data["name"]} showing declining performance trend ({performance_trend:.1%})',
            'actions': [
                'Skills assessment and gap analysis',
                'Targeted training in weak areas',
                'Assign mentor or buddy',
                'Project rotation for skill development',
                'Weekly 1:1s with clear goals',
                'Performance improvement plan (if needed)',
            ],
            'urgency_days': 14,
            'performance_trend': performance_trend,
            'employee_id': employee_data['id'],
            'employee_name': employee_data['name'],
            'department': employee_data['department'],
            'created_at': datetime.utcnow(),
        }
    
    def _create_engagement_intervention(
        self, 
        employee_data: Dict[str, Any],
        trust_score: float,
        engagement: float
    ) -> Dict[str, Any]:
        """Create engagement intervention"""
        return {
            'category': 'engagement',
            'priority': 'high',
            'scope': 'individual',
            'title': 'Engagement & Retention Initiative',
            'description': f'{employee_data["name"]} showing low engagement (trust: {trust_score:.1f}, engagement: {engagement:.1%})',
            'actions': [
                'Career development planning session',
                'Explore growth opportunities',
                'Offer project leadership role',
                'Cross-team collaboration opportunities',
                'Recognition and appreciation',
                'Team building activities',
                'Stay interview to understand concerns',
            ],
            'urgency_days': 7,
            'trust_score': trust_score,
            'engagement_score': engagement,
            'employee_id': employee_data['id'],
            'employee_name': employee_data['name'],
            'department': employee_data['department'],
            'created_at': datetime.utcnow(),
        }
    
    def _create_development_intervention(
        self, 
        employee_data: Dict[str, Any],
        trust_score: float,
        performance_trend: float
    ) -> Dict[str, Any]:
        """Create development intervention for high performers"""
        return {
            'category': 'development',
            'priority': 'low',
            'scope': 'individual',
            'title': 'Leadership & Growth Opportunities',
            'description': f'{employee_data["name"]} is a strong performer - invest in development',
            'actions': [
                'Leadership training program',
                'Mentorship role for junior team members',
                'Strategic project assignment',
                'Conference or workshop attendance',
                'Promotion discussion',
                'Stretch assignments',
            ],
            'urgency_days': 30,
            'trust_score': trust_score,
            'performance_trend': performance_trend,
            'employee_id': employee_data['id'],
            'employee_name': employee_data['name'],
            'department': employee_data['department'],
            'created_at': datetime.utcnow(),
        }
    
    def _create_team_intervention(
        self, 
        employee_data: Dict[str, Any],
        team_issues: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create team dynamics intervention"""
        return {
            'category': 'team',
            'priority': 'medium',
            'scope': 'individual',
            'title': 'Team Collaboration Support',
            'description': f'{employee_data["name"]} experiencing team dynamics issues',
            'actions': [
                'Team dynamics assessment',
                'Conflict resolution session',
                'Communication training',
                'Team building activities',
                'Role clarification',
                'Cross-functional collaboration',
            ],
            'urgency_days': 14,
            'team_issues': team_issues,
            'employee_id': employee_data['id'],
            'employee_name': employee_data['name'],
            'department': employee_data['department'],
            'created_at': datetime.utcnow(),
        }
    
    # ========================================================================
    # DATA GATHERING
    # ========================================================================
    
    async def _get_trust_score(self, employee_id: str, db: AsyncSession) -> float:
        """Get latest trust score for employee"""
        try:
            result = await db.execute(
                select(TrustScore.total_score)
                .where(TrustScore.employee_id == uuid.UUID(employee_id))
                .order_by(TrustScore.timestamp.desc())
                .limit(1)
            )
            score = result.scalar()
            return float(score) if score else 50.0
        except Exception as e:
            logger.error(f"Error fetching trust score: {e}")
            return 50.0
    
    async def _predict_burnout(self, employee_id: str, db: AsyncSession) -> float:
        """
        Predict burnout risk based on signals
        
        Factors:
        - Long work hours
        - Weekend work
        - Late night work
        - Declining engagement
        - Stress indicators
        """
        try:
            # Get recent signals (last 30 days)
            cutoff = datetime.utcnow() - timedelta(days=30)
            
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
            
            if not signals:
                return 0.0
            
            # Calculate burnout indicators
            risk_score = 0.0
            
            # Group by day
            daily_signals = defaultdict(list)
            for signal in signals:
                day = signal.timestamp.date()
                daily_signals[day].append(signal)
            
            # Analyze each day
            long_days = 0
            weekend_days = 0
            late_nights = 0
            
            for day, day_signals in daily_signals.items():
                if not day_signals:
                    continue
                
                # Calculate work hours
                timestamps = [s.timestamp for s in day_signals]
                work_start = min(timestamps)
                work_end = max(timestamps)
                work_hours = (work_end - work_start).total_seconds() / 3600
                
                # Long work day (>10 hours)
                if work_hours > 10:
                    long_days += 1
                    risk_score += 0.05
                
                # Weekend work
                if work_start.weekday() >= 5:
                    weekend_days += 1
                    risk_score += 0.03
                
                # Late night work (after 8 PM)
                if work_end.hour >= 20:
                    late_nights += 1
                    risk_score += 0.02
            
            # Normalize risk score
            total_days = len(daily_signals)
            if total_days > 0:
                # High frequency of overwork
                if long_days / total_days > 0.5:
                    risk_score += 0.2
                if weekend_days / total_days > 0.3:
                    risk_score += 0.15
                if late_nights / total_days > 0.4:
                    risk_score += 0.1
            
            # Cap at 1.0
            return min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error predicting burnout: {e}")
            return 0.0
    
    async def _get_performance_trend(self, employee_id: str, db: AsyncSession) -> float:
        """
        Calculate performance trend
        
        Returns:
            Positive = improving, Negative = declining
        """
        try:
            # Get trust scores from last 60 days
            cutoff = datetime.utcnow() - timedelta(days=60)
            
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
            
            if len(scores) < 2:
                return 0.0
            
            # Calculate trend (simple linear regression)
            score_values = [s[0] for s in scores]
            
            # Compare recent vs older
            mid_point = len(score_values) // 2
            recent_avg = np.mean(score_values[mid_point:])
            older_avg = np.mean(score_values[:mid_point])
            
            # Normalize to -1 to 1 range
            trend = (recent_avg - older_avg) / 100.0
            
            return trend
            
        except Exception as e:
            logger.error(f"Error calculating performance trend: {e}")
            return 0.0
    
    async def _calculate_engagement(self, employee_id: str, db: AsyncSession) -> float:
        """
        Calculate engagement score
        
        Based on:
        - Activity level
        - Collaboration
        - Responsiveness
        """
        try:
            # Get recent signals (last 30 days)
            cutoff = datetime.utcnow() - timedelta(days=30)
            
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
            
            if not signals:
                return 0.5
            
            # Engagement indicators
            engagement_signals = [
                s for s in signals
                if s.signal_type in ['task_completed', 'code_commit', 'meeting_attended']
            ]
            
            # Calculate engagement rate
            engagement_rate = len(engagement_signals) / len(signals)
            
            return engagement_rate
            
        except Exception as e:
            logger.error(f"Error calculating engagement: {e}")
            return 0.5
    
    async def _get_employee_data(self, employee_id: str, db: AsyncSession) -> Dict[str, Any]:
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
    
    async def _detect_team_issues(self, employee_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """Detect team dynamics issues"""
        # Simplified - would analyze collaboration patterns, conflicts, etc.
        return None
    
    async def _get_team_members(
        self, 
        team_id: Optional[str],
        department: Optional[str],
        db: AsyncSession
    ) -> List[str]:
        """Get team member IDs"""
        try:
            query = select(Employee.id).where(Employee.status == 'active')
            
            if department:
                query = query.where(Employee.department == department)
            
            result = await db.execute(query)
            return [str(row[0]) for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Error fetching team members: {e}")
            return []
    
    async def _analyze_team_burnout(
        self, 
        team_members: List[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Analyze team burnout levels"""
        risks = []
        for member_id in team_members:
            risk = await self._predict_burnout(member_id, db)
            risks.append(risk)
        
        return {
            'avg_risk': np.mean(risks) if risks else 0.0,
            'max_risk': max(risks) if risks else 0.0,
            'high_risk_count': sum(1 for r in risks if r > 0.7),
        }
    
    async def _analyze_team_performance(
        self, 
        team_members: List[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Analyze team performance trends"""
        trends = []
        for member_id in team_members:
            trend = await self._get_performance_trend(member_id, db)
            trends.append(trend)
        
        return {
            'avg_trend': np.mean(trends) if trends else 0.0,
            'declining_count': sum(1 for t in trends if t < -0.1),
            'improving_count': sum(1 for t in trends if t > 0.1),
        }
    
    async def _analyze_team_balance(
        self, 
        team_members: List[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Analyze team balance"""
        # Simplified - would analyze workload distribution, skill balance, etc.
        return {
            'is_balanced': True,
            'issue': None,
        }
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _prioritize_interventions(
        self, 
        interventions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Sort interventions by priority"""
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        
        return sorted(
            interventions,
            key=lambda x: priority_order.get(x['priority'], 999)
        )
    
    async def _store_interventions(
        self, 
        employee_id: str,
        interventions: List[Dict[str, Any]],
        db: AsyncSession
    ) -> None:
        """Store intervention recommendations"""
        # In production, would store to database table
        # For now, just log
        logger.info(
            f"Storing {len(interventions)} interventions for employee {employee_id}"
        )
