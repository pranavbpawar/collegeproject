"""
Adaptive Monitoring Controller
Adjusts monitoring thresholds based on context to prevent false positives
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
import calendar


# ============================================================================
# DATA CLASSES
# ============================================================================

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectPhase(Enum):
    """Project lifecycle phases"""
    PLANNING = "planning"
    DEVELOPMENT = "development"
    TESTING = "testing"
    LAUNCH = "launch"
    MAINTENANCE = "maintenance"
    CRISIS = "crisis"


@dataclass
class EmployeeContext:
    """Employee context information"""
    employee_id: str
    role: str
    department: str
    seniority_level: str
    tenure_months: int
    current_projects: List[str]
    team_size: int


@dataclass
class SystemContext:
    """System-wide context"""
    current_month: int
    current_day_of_week: int
    current_hour: int
    is_holiday_season: bool
    is_end_of_quarter: bool
    is_end_of_year: bool
    project_phase: ProjectPhase
    company_event: Optional[str]


@dataclass
class AdaptiveThresholds:
    """Adaptive monitoring thresholds"""
    # Meeting thresholds
    meetings_max_per_day: float
    meetings_max_per_week: float
    
    # Response time thresholds (minutes)
    email_response_max: float
    urgent_response_max: float
    
    # Work hours thresholds
    work_hours_max_per_day: float
    work_hours_max_per_week: float
    late_night_threshold_hour: int
    
    # Productivity thresholds
    deadline_miss_rate_max: float
    task_completion_rate_min: float
    
    # Engagement thresholds
    collaboration_min_per_week: float
    code_review_min_per_week: float
    
    # Anomaly thresholds
    anomaly_score_threshold: float
    
    # Trust score thresholds
    trust_score_min: float


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_level: RiskLevel
    trust_score: float
    recent_anomalies: int
    burnout_score: float
    factors: List[str]
    confidence: float


# ============================================================================
# ADAPTIVE MONITORING CONTROLLER
# ============================================================================

class AdaptiveMonitoringController:
    """
    Adaptive Monitoring Controller
    
    Adjusts monitoring thresholds based on:
    - Employee role and seniority
    - Department and team context
    - Project phase
    - Time of year (holidays, quarter-end)
    - Individual history and baseline
    - Current risk level
    
    Prevents false positives through context-aware thresholds.
    """
    
    # Base thresholds by role
    ROLE_THRESHOLDS = {
        'manager': {
            'meetings_per_day': 8,
            'meetings_per_week': 35,
            'email_response': 60,
            'work_hours_day': 10,
            'work_hours_week': 50
        },
        'engineer': {
            'meetings_per_day': 4,
            'meetings_per_week': 20,
            'email_response': 120,
            'work_hours_day': 9,
            'work_hours_week': 45
        },
        'support': {
            'meetings_per_day': 10,
            'meetings_per_week': 45,
            'email_response': 30,
            'work_hours_day': 9,
            'work_hours_week': 45
        },
        'sales': {
            'meetings_per_day': 12,
            'meetings_per_week': 50,
            'email_response': 45,
            'work_hours_day': 10,
            'work_hours_week': 50
        },
        'executive': {
            'meetings_per_day': 10,
            'meetings_per_week': 45,
            'email_response': 90,
            'work_hours_day': 11,
            'work_hours_week': 55
        },
        'default': {
            'meetings_per_day': 5,
            'meetings_per_week': 25,
            'email_response': 90,
            'work_hours_day': 9,
            'work_hours_week': 45
        }
    }
    
    # Department multipliers
    DEPARTMENT_MULTIPLIERS = {
        'engineering': {'meetings': 0.8, 'work_hours': 1.0},
        'sales': {'meetings': 1.3, 'work_hours': 1.1},
        'support': {'meetings': 1.2, 'work_hours': 1.0},
        'marketing': {'meetings': 1.1, 'work_hours': 1.0},
        'hr': {'meetings': 1.0, 'work_hours': 0.9},
        'finance': {'meetings': 0.9, 'work_hours': 1.1}
    }
    
    # Seniority multipliers
    SENIORITY_MULTIPLIERS = {
        'junior': {'meetings': 0.7, 'work_hours': 0.9, 'response_time': 1.2},
        'mid': {'meetings': 1.0, 'work_hours': 1.0, 'response_time': 1.0},
        'senior': {'meetings': 1.2, 'work_hours': 1.1, 'response_time': 0.9},
        'lead': {'meetings': 1.4, 'work_hours': 1.2, 'response_time': 0.8},
        'principal': {'meetings': 1.3, 'work_hours': 1.2, 'response_time': 0.8}
    }
    
    def __init__(self, db_connection=None):
        """
        Initialize Adaptive Monitoring Controller
        
        Args:
            db_connection: Database connection
        """
        self.db = db_connection
        self.logger = logging.getLogger(__name__)
    
    # ========================================================================
    # MAIN THRESHOLD CALCULATION
    # ========================================================================
    
    async def adjust_thresholds(
        self,
        employee_id: str
    ) -> AdaptiveThresholds:
        """
        Calculate adaptive thresholds for employee
        
        Args:
            employee_id: Employee identifier
        
        Returns:
            AdaptiveThresholds with context-aware values
        """
        # Get employee context
        employee_ctx = await self.get_employee_context(employee_id)
        
        # Get system context
        system_ctx = self.get_system_context()
        
        # Get baseline
        baseline = await self.get_employee_baseline(employee_id)
        
        # Assess current risk
        risk = await self.assess_risk(employee_id)
        
        # Calculate thresholds
        thresholds = self._calculate_thresholds(
            employee_ctx,
            system_ctx,
            baseline,
            risk
        )
        
        return thresholds
    
    def _calculate_thresholds(
        self,
        employee_ctx: EmployeeContext,
        system_ctx: SystemContext,
        baseline: Dict[str, Any],
        risk: RiskAssessment
    ) -> AdaptiveThresholds:
        """
        Calculate all adaptive thresholds
        
        Args:
            employee_ctx: Employee context
            system_ctx: System context
            baseline: Employee baseline
            risk: Risk assessment
        
        Returns:
            AdaptiveThresholds
        """
        # Get base thresholds for role
        base = self.ROLE_THRESHOLDS.get(
            employee_ctx.role.lower(),
            self.ROLE_THRESHOLDS['default']
        )
        
        # Calculate meeting thresholds
        meetings_day = self.calc_meeting_threshold(
            employee_ctx, system_ctx, base['meetings_per_day']
        )
        meetings_week = self.calc_meeting_threshold(
            employee_ctx, system_ctx, base['meetings_per_week']
        )
        
        # Calculate response time thresholds
        email_response = self.calc_response_threshold(
            employee_ctx, system_ctx, base['email_response']
        )
        urgent_response = email_response * 0.5  # Urgent = 50% of normal
        
        # Calculate work hours thresholds
        work_hours_day, work_hours_week = self.calc_work_hours_threshold(
            employee_ctx, system_ctx, risk,
            base['work_hours_day'], base['work_hours_week']
        )
        
        # Calculate late night threshold
        late_night_hour = self.calc_late_night_threshold(employee_ctx, system_ctx)
        
        # Calculate productivity thresholds
        deadline_miss_rate = self.calc_deadline_threshold(risk, baseline)
        task_completion_min = self.calc_completion_threshold(risk, baseline)
        
        # Calculate engagement thresholds
        collaboration_min = self.calc_collaboration_threshold(employee_ctx, system_ctx)
        code_review_min = self.calc_code_review_threshold(employee_ctx)
        
        # Calculate anomaly threshold
        anomaly_threshold = self.calc_anomaly_threshold(risk)
        
        # Calculate trust score threshold
        trust_min = self.calc_trust_threshold(employee_ctx, risk)
        
        return AdaptiveThresholds(
            meetings_max_per_day=meetings_day,
            meetings_max_per_week=meetings_week,
            email_response_max=email_response,
            urgent_response_max=urgent_response,
            work_hours_max_per_day=work_hours_day,
            work_hours_max_per_week=work_hours_week,
            late_night_threshold_hour=late_night_hour,
            deadline_miss_rate_max=deadline_miss_rate,
            task_completion_rate_min=task_completion_min,
            collaboration_min_per_week=collaboration_min,
            code_review_min_per_week=code_review_min,
            anomaly_score_threshold=anomaly_threshold,
            trust_score_min=trust_min
        )
    
    # ========================================================================
    # THRESHOLD CALCULATION FUNCTIONS
    # ========================================================================
    
    def calc_meeting_threshold(
        self,
        employee_ctx: EmployeeContext,
        system_ctx: SystemContext,
        base: float
    ) -> float:
        """
        Calculate meeting threshold with context adjustments
        
        Args:
            employee_ctx: Employee context
            system_ctx: System context
            base: Base threshold
        
        Returns:
            Adjusted meeting threshold
        """
        threshold = base
        
        # Adjust for department
        dept_mult = self.DEPARTMENT_MULTIPLIERS.get(
            employee_ctx.department.lower(), {}
        ).get('meetings', 1.0)
        threshold *= dept_mult
        
        # Adjust for seniority
        seniority_mult = self.SENIORITY_MULTIPLIERS.get(
            employee_ctx.seniority_level.lower(), {}
        ).get('meetings', 1.0)
        threshold *= seniority_mult
        
        # Adjust for project phase
        if system_ctx.project_phase == ProjectPhase.LAUNCH:
            threshold *= 1.5  # More meetings during launch
        elif system_ctx.project_phase == ProjectPhase.CRISIS:
            threshold *= 1.8  # Even more during crisis
        elif system_ctx.project_phase == ProjectPhase.DEVELOPMENT:
            threshold *= 0.9  # Fewer during development
        
        # Adjust for time of year
        if system_ctx.is_holiday_season:
            threshold *= 0.7  # Fewer meetings during holidays
        elif system_ctx.is_end_of_quarter:
            threshold *= 1.2  # More at quarter-end
        
        # Adjust for team size
        if employee_ctx.team_size > 10:
            threshold *= 1.2  # More meetings for large teams
        elif employee_ctx.team_size < 3:
            threshold *= 0.8  # Fewer for small teams
        
        return round(threshold, 1)
    
    def calc_response_threshold(
        self,
        employee_ctx: EmployeeContext,
        system_ctx: SystemContext,
        base: float
    ) -> float:
        """
        Calculate response time threshold
        
        Args:
            employee_ctx: Employee context
            system_ctx: System context
            base: Base threshold (minutes)
        
        Returns:
            Adjusted response time threshold
        """
        threshold = base
        
        # Adjust for seniority
        seniority_mult = self.SENIORITY_MULTIPLIERS.get(
            employee_ctx.seniority_level.lower(), {}
        ).get('response_time', 1.0)
        threshold *= seniority_mult
        
        # Adjust for role
        if employee_ctx.role.lower() == 'support':
            threshold *= 0.5  # Support needs faster response
        elif employee_ctx.role.lower() == 'engineer':
            threshold *= 1.2  # Engineers can take longer
        
        # Adjust for time of day
        if 9 <= system_ctx.current_hour < 17:
            threshold *= 0.8  # Faster during business hours
        else:
            threshold *= 1.5  # Slower outside business hours
        
        return round(threshold, 1)
    
    def calc_work_hours_threshold(
        self,
        employee_ctx: EmployeeContext,
        system_ctx: SystemContext,
        risk: RiskAssessment,
        base_day: float,
        base_week: float
    ) -> Tuple[float, float]:
        """
        Calculate work hours thresholds
        
        Args:
            employee_ctx: Employee context
            system_ctx: System context
            risk: Risk assessment
            base_day: Base daily hours
            base_week: Base weekly hours
        
        Returns:
            Tuple of (daily_threshold, weekly_threshold)
        """
        day_threshold = base_day
        week_threshold = base_week
        
        # Adjust for department
        dept_mult = self.DEPARTMENT_MULTIPLIERS.get(
            employee_ctx.department.lower(), {}
        ).get('work_hours', 1.0)
        day_threshold *= dept_mult
        week_threshold *= dept_mult
        
        # Adjust for seniority
        seniority_mult = self.SENIORITY_MULTIPLIERS.get(
            employee_ctx.seniority_level.lower(), {}
        ).get('work_hours', 1.0)
        day_threshold *= seniority_mult
        week_threshold *= seniority_mult
        
        # Adjust for project phase
        if system_ctx.project_phase == ProjectPhase.LAUNCH:
            day_threshold *= 1.2
            week_threshold *= 1.3
        elif system_ctx.project_phase == ProjectPhase.CRISIS:
            day_threshold *= 1.3
            week_threshold *= 1.4
        
        # Adjust for risk level (stricter for high risk)
        if risk.risk_level == RiskLevel.HIGH:
            day_threshold *= 0.9
            week_threshold *= 0.9
        elif risk.risk_level == RiskLevel.CRITICAL:
            day_threshold *= 0.8
            week_threshold *= 0.8
        
        # Adjust for time of year
        if system_ctx.is_end_of_quarter:
            day_threshold *= 1.1
            week_threshold *= 1.15
        
        return round(day_threshold, 1), round(week_threshold, 1)
    
    def calc_late_night_threshold(
        self,
        employee_ctx: EmployeeContext,
        system_ctx: SystemContext
    ) -> int:
        """
        Calculate late night work threshold hour
        
        Args:
            employee_ctx: Employee context
            system_ctx: System context
        
        Returns:
            Hour (0-23) after which work is considered late night
        """
        base_hour = 21  # 9 PM default
        
        # Adjust for role
        if employee_ctx.role.lower() in ['support', 'sales']:
            base_hour = 22  # Later for customer-facing roles
        elif employee_ctx.role.lower() == 'engineer':
            base_hour = 22  # Engineers often work later
        
        # Adjust for project phase
        if system_ctx.project_phase in [ProjectPhase.LAUNCH, ProjectPhase.CRISIS]:
            base_hour = 23  # More lenient during critical phases
        
        return base_hour
    
    def calc_deadline_threshold(
        self,
        risk: RiskAssessment,
        baseline: Dict[str, Any]
    ) -> float:
        """
        Calculate deadline miss rate threshold
        
        Args:
            risk: Risk assessment
            baseline: Employee baseline
        
        Returns:
            Maximum acceptable deadline miss rate (0-1)
        """
        base_rate = 0.15  # 15% baseline
        
        # Adjust based on historical performance
        historical_rate = baseline.get('deadline_miss_rate', 0.10)
        if historical_rate < 0.05:
            base_rate = 0.10  # Stricter for high performers
        elif historical_rate > 0.20:
            base_rate = 0.25  # More lenient for those struggling
        
        # Adjust for risk level
        if risk.risk_level == RiskLevel.HIGH:
            base_rate *= 1.2  # More lenient when at risk
        elif risk.risk_level == RiskLevel.CRITICAL:
            base_rate *= 1.3
        
        return min(0.30, base_rate)  # Cap at 30%
    
    def calc_completion_threshold(
        self,
        risk: RiskAssessment,
        baseline: Dict[str, Any]
    ) -> float:
        """
        Calculate task completion rate threshold
        
        Args:
            risk: Risk assessment
            baseline: Employee baseline
        
        Returns:
            Minimum acceptable completion rate (0-1)
        """
        base_rate = 0.80  # 80% baseline
        
        # Adjust based on historical performance
        historical_rate = baseline.get('task_completion_rate', 0.85)
        if historical_rate > 0.95:
            base_rate = 0.90  # Higher expectations for high performers
        elif historical_rate < 0.70:
            base_rate = 0.70  # Lower for those struggling
        
        # Adjust for risk level
        if risk.risk_level == RiskLevel.HIGH:
            base_rate *= 0.9  # More lenient when at risk
        elif risk.risk_level == RiskLevel.CRITICAL:
            base_rate *= 0.85
        
        return max(0.60, base_rate)  # Floor at 60%
    
    def calc_collaboration_threshold(
        self,
        employee_ctx: EmployeeContext,
        system_ctx: SystemContext
    ) -> float:
        """
        Calculate collaboration minimum threshold
        
        Args:
            employee_ctx: Employee context
            system_ctx: System context
        
        Returns:
            Minimum collaborations per week
        """
        base = 5.0  # 5 collaborations per week
        
        # Adjust for role
        if employee_ctx.role.lower() == 'manager':
            base = 15.0
        elif employee_ctx.role.lower() == 'engineer':
            base = 8.0
        elif employee_ctx.role.lower() in ['support', 'sales']:
            base = 10.0
        
        # Adjust for team size
        if employee_ctx.team_size > 10:
            base *= 1.3
        elif employee_ctx.team_size < 3:
            base *= 0.7
        
        # Adjust for project phase
        if system_ctx.project_phase == ProjectPhase.DEVELOPMENT:
            base *= 1.2  # More collaboration during development
        
        return round(base, 1)
    
    def calc_code_review_threshold(
        self,
        employee_ctx: EmployeeContext
    ) -> float:
        """
        Calculate code review minimum threshold
        
        Args:
            employee_ctx: Employee context
        
        Returns:
            Minimum code reviews per week
        """
        if employee_ctx.role.lower() != 'engineer':
            return 0.0  # Not applicable for non-engineers
        
        base = 3.0  # 3 reviews per week
        
        # Adjust for seniority
        if employee_ctx.seniority_level.lower() in ['senior', 'lead', 'principal']:
            base = 5.0  # More reviews for senior engineers
        elif employee_ctx.seniority_level.lower() == 'junior':
            base = 1.0  # Fewer for juniors
        
        return base
    
    def calc_anomaly_threshold(self, risk: RiskAssessment) -> float:
        """
        Calculate anomaly score threshold
        
        Args:
            risk: Risk assessment
        
        Returns:
            Anomaly score threshold (0-100)
        """
        base = 50.0  # 50 baseline
        
        # Adjust for risk level
        if risk.risk_level == RiskLevel.LOW:
            base = 60.0  # Higher threshold (less sensitive)
        elif risk.risk_level == RiskLevel.HIGH:
            base = 40.0  # Lower threshold (more sensitive)
        elif risk.risk_level == RiskLevel.CRITICAL:
            base = 30.0  # Very sensitive
        
        return base
    
    def calc_trust_threshold(
        self,
        employee_ctx: EmployeeContext,
        risk: RiskAssessment
    ) -> float:
        """
        Calculate trust score minimum threshold
        
        Args:
            employee_ctx: Employee context
            risk: Risk assessment
        
        Returns:
            Minimum trust score (0-100)
        """
        base = 60.0  # 60 baseline
        
        # Adjust for tenure
        if employee_ctx.tenure_months < 6:
            base = 50.0  # More lenient for new employees
        elif employee_ctx.tenure_months > 24:
            base = 65.0  # Higher expectations for veterans
        
        # Adjust for seniority
        if employee_ctx.seniority_level.lower() in ['senior', 'lead', 'principal']:
            base = 70.0  # Higher for senior roles
        
        return base
    
    # ========================================================================
    # RISK ASSESSMENT
    # ========================================================================
    
    async def assess_risk(self, employee_id: str) -> RiskAssessment:
        """
        Assess current risk level for employee
        
        Args:
            employee_id: Employee identifier
        
        Returns:
            RiskAssessment
        """
        # Get current trust score
        trust_score = await self.get_current_trust_score(employee_id)
        
        # Get recent anomalies
        anomalies = await self.get_recent_anomalies(employee_id, days=7)
        
        # Get burnout score
        burnout_score = await self.get_burnout_score(employee_id)
        
        # Determine risk level
        risk_level, factors = self._determine_risk_level(
            trust_score, anomalies, burnout_score
        )
        
        # Calculate confidence
        confidence = self._calculate_risk_confidence(trust_score, anomalies, burnout_score)
        
        return RiskAssessment(
            risk_level=risk_level,
            trust_score=trust_score,
            recent_anomalies=anomalies,
            burnout_score=burnout_score,
            factors=factors,
            confidence=confidence
        )
    
    def _determine_risk_level(
        self,
        trust_score: float,
        anomalies: int,
        burnout_score: float
    ) -> Tuple[RiskLevel, List[str]]:
        """
        Determine risk level from metrics
        
        Args:
            trust_score: Trust score (0-100)
            anomalies: Recent anomaly count
            burnout_score: Burnout score (0-100)
        
        Returns:
            Tuple of (RiskLevel, factors)
        """
        factors = []
        score = 0
        
        # Trust score factor
        if trust_score < 40:
            score += 40
            factors.append("Very low trust score")
        elif trust_score < 60:
            score += 20
            factors.append("Low trust score")
        
        # Anomaly factor
        if anomalies > 5:
            score += 30
            factors.append("Many recent anomalies")
        elif anomalies > 2:
            score += 15
            factors.append("Some recent anomalies")
        
        # Burnout factor
        if burnout_score > 75:
            score += 30
            factors.append("Critical burnout risk")
        elif burnout_score > 50:
            score += 15
            factors.append("High burnout risk")
        
        # Determine level
        if score >= 60:
            return RiskLevel.CRITICAL, factors
        elif score >= 35:
            return RiskLevel.HIGH, factors
        elif score >= 15:
            return RiskLevel.MEDIUM, factors
        else:
            return RiskLevel.LOW, factors
    
    def _calculate_risk_confidence(
        self,
        trust_score: float,
        anomalies: int,
        burnout_score: float
    ) -> float:
        """
        Calculate confidence in risk assessment
        
        Args:
            trust_score: Trust score
            anomalies: Anomaly count
            burnout_score: Burnout score
        
        Returns:
            Confidence (0-1)
        """
        confidence = 0.5  # Base
        
        # More data = higher confidence
        if trust_score > 0:
            confidence += 0.2
        if burnout_score > 0:
            confidence += 0.2
        if anomalies >= 0:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    # ========================================================================
    # CONTEXT RETRIEVAL
    # ========================================================================
    
    async def get_employee_context(self, employee_id: str) -> EmployeeContext:
        """Get employee context from database"""
        if not self.db:
            return self._get_mock_employee_context()
        
        try:
            query = """
                SELECT
                    id as employee_id,
                    role,
                    department,
                    seniority_level,
                    EXTRACT(MONTH FROM AGE(NOW(), hire_date))::INTEGER as tenure_months,
                    ARRAY[]::TEXT[] as current_projects,
                    5 as team_size
                FROM employees
                WHERE id = $1
            """
            result = await self.db.fetchrow(query, employee_id)
            
            if result:
                return EmployeeContext(**dict(result))
            else:
                return self._get_mock_employee_context()
        except Exception as e:
            self.logger.error(f"Error getting employee context: {e}")
            return self._get_mock_employee_context()
    
    def get_system_context(self) -> SystemContext:
        """Get current system context"""
        now = datetime.utcnow()
        
        return SystemContext(
            current_month=now.month,
            current_day_of_week=now.weekday(),
            current_hour=now.hour,
            is_holiday_season=(now.month in [11, 12, 1]),
            is_end_of_quarter=(now.month in [3, 6, 9, 12] and now.day > 25),
            is_end_of_year=(now.month == 12 and now.day > 20),
            project_phase=ProjectPhase.DEVELOPMENT,  # Would be dynamic
            company_event=None
        )
    
    async def get_employee_baseline(self, employee_id: str) -> Dict[str, Any]:
        """Get employee baseline metrics"""
        if not self.db:
            return {
                'deadline_miss_rate': 0.10,
                'task_completion_rate': 0.85
            }
        
        # Would fetch from database
        return {
            'deadline_miss_rate': 0.10,
            'task_completion_rate': 0.85
        }
    
    async def get_current_trust_score(self, employee_id: str) -> float:
        """Get current trust score"""
        if not self.db:
            return 75.0
        
        # Would fetch from database
        return 75.0
    
    async def get_recent_anomalies(self, employee_id: str, days: int) -> int:
        """Get recent anomaly count"""
        if not self.db:
            return 1
        
        # Would fetch from database
        return 1
    
    async def get_burnout_score(self, employee_id: str) -> float:
        """Get burnout score"""
        if not self.db:
            return 35.0
        
        # Would fetch from database
        return 35.0
    
    def _get_mock_employee_context(self) -> EmployeeContext:
        """Get mock employee context for testing"""
        return EmployeeContext(
            employee_id="emp_001",
            role="engineer",
            department="engineering",
            seniority_level="mid",
            tenure_months=18,
            current_projects=["project_a", "project_b"],
            team_size=7
        )
