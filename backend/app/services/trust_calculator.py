"""
TBAPS Trust Score Calculator
Calculates daily trust scores combining 4 weighted components with time-decay
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
from app.models import Employee, SignalEvent, BaselineProfile, TrustScore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/tbaps/trust_calculator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TrustCalculator:
    """
    Trust Score Calculator
    
    Calculates comprehensive trust scores combining:
    - Outcome Reliability (35%): Task completion, quality, deadlines
    - Behavioral Consistency (30%): Pattern stability, response times, collaboration
    - Security Hygiene (20%): MFA, VPN, password, phishing safety
    - Psychological Wellbeing (15%): Engagement, stress, sentiment
    
    Applies time-decay weighting to recent events (0-7 days: 100%, 8-14: 80%, 15-30: 60%)
    """
    
    # Component weights (must sum to 1.0)
    WEIGHTS = {
        'outcome': 0.35,
        'behavioral': 0.30,
        'security': 0.20,
        'wellbeing': 0.15
    }
    
    # Sub-component weights
    OUTCOME_WEIGHTS = {
        'completion': 0.40,
        'quality': 0.35,
        'deadline': 0.25
    }
    
    BEHAVIORAL_WEIGHTS = {
        'pattern_deviation': 0.30,
        'response_time': 0.25,
        'collaboration': 0.20,
        'browsing_productivity': 0.25  # NEW: Browsing behavior
    }
    
    SECURITY_WEIGHTS = {
        'mfa': 0.33,
        'vpn': 0.33,
        'phishing': 0.34
    }
    
    WELLBEING_WEIGHTS = {
        'engagement': 0.35,
        'stress': 0.40,
        'sentiment': 0.25
    }
    
    # Time decay factors
    TIME_DECAY = {
        (0, 7): 1.0,      # Recent: full weight
        (8, 14): 0.8,     # Week old: 80%
        (15, 30): 0.6,    # Month old: 60%
    }
    
    def __init__(self, window_days: int = 30):
        """
        Initialize trust calculator
        
        Args:
            window_days: Number of days to analyze (default: 30)
        """
        self.window_days = window_days
        logger.info(f"TrustCalculator initialized with {window_days}-day window")
    
    async def calculate_daily_scores(self) -> Dict[str, Any]:
        """
        Calculate trust scores for all active employees
        
        Returns:
            Summary statistics of calculation run
        """
        logger.info("Starting daily trust score calculation for all employees")
        
        start_time = datetime.utcnow()
        total_employees = 0
        successful_calculations = 0
        failed_calculations = 0
        
        async for db in get_db():
            try:
                # Get all active employees
                result = await db.execute(
                    select(Employee).where(Employee.status == 'active')
                )
                employees = result.scalars().all()
                total_employees = len(employees)
                
                logger.info(f"Processing {total_employees} active employees")
                
                for employee in employees:
                    try:
                        score = await self.calculate_trust_score(
                            str(employee.id),
                            db=db
                        )
                        
                        if score is not None:
                            await self._store_score(str(employee.id), score, db)
                            successful_calculations += 1
                            logger.debug(f"Calculated score for {employee.email}: {score['total']:.2f}")
                        else:
                            failed_calculations += 1
                            logger.warning(f"Insufficient data for {employee.email}")
                    
                    except Exception as e:
                        failed_calculations += 1
                        logger.error(f"Error calculating score for {employee.email}: {e}")
                
                await db.commit()
                
            except Exception as e:
                logger.error(f"Database error during calculation: {e}")
                await db.rollback()
                raise
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        summary = {
            'total_employees': total_employees,
            'successful': successful_calculations,
            'failed': failed_calculations,
            'duration_seconds': duration,
            'timestamp': start_time
        }
        
        logger.info(
            f"Trust calculation complete: {successful_calculations}/{total_employees} "
            f"successful in {duration:.2f}s"
        )
        
        return summary
    
    async def calculate_trust_score(
        self,
        employee_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate trust score for a single employee
        
        Args:
            employee_id: Employee UUID
            db: Database session (optional)
        
        Returns:
            Dictionary with component scores and total, or None if insufficient data
        """
        should_close = False
        if db is None:
            async for session in get_db():
                db = session
                should_close = True
                break
        
        try:
            logger.debug(f"Calculating trust score for employee {employee_id}")
            
            # Get signals and baseline
            cutoff_date = datetime.utcnow() - timedelta(days=self.window_days)
            signals = await self._get_signals(employee_id, cutoff_date, db)
            baseline = await self._get_baseline(employee_id, db)
            
            if not signals:
                logger.warning(f"No signals found for employee {employee_id}")
                return None
            
            if not baseline:
                logger.warning(f"No baseline found for employee {employee_id}")
                return None
            
            # Calculate component scores
            outcome_score = await self._calc_outcome_score(signals, db)
            behavioral_score = await self._calc_behavioral_score(signals, baseline, db)
            security_score = await self._calc_security_score(signals, baseline, db)
            wellbeing_score = await self._calc_wellbeing_score(signals, db)
            
            # Calculate time decay factor
            time_decay = self._calculate_time_decay(signals)
            
            # Combine with weights
            total_score = (
                outcome_score * self.WEIGHTS['outcome'] +
                behavioral_score * self.WEIGHTS['behavioral'] +
                security_score * self.WEIGHTS['security'] +
                wellbeing_score * self.WEIGHTS['wellbeing']
            )
            
            # Apply time decay
            total_score *= time_decay
            
            # Normalize to 0-100
            total_score = max(0.0, min(100.0, total_score))
            
            result = {
                'outcome': round(outcome_score, 2),
                'behavioral': round(behavioral_score, 2),
                'security': round(security_score, 2),
                'wellbeing': round(wellbeing_score, 2),
                'total': round(total_score, 2),
                'time_decay_factor': round(time_decay, 3),
                'timestamp': datetime.utcnow()
            }
            
            logger.debug(
                f"Score calculated for {employee_id}: "
                f"Total={result['total']}, O={result['outcome']}, "
                f"B={result['behavioral']}, S={result['security']}, W={result['wellbeing']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating trust score for {employee_id}: {e}")
            raise
        
        finally:
            if should_close and db:
                await db.close()
    
    async def _get_signals(
        self,
        employee_id: str,
        cutoff_date: datetime,
        db: AsyncSession
    ) -> List[SignalEvent]:
        """Get signal events for employee within date range"""
        try:
            result = await db.execute(
                select(SignalEvent)
                .where(
                    and_(
                        SignalEvent.employee_id == uuid.UUID(employee_id),
                        SignalEvent.timestamp >= cutoff_date
                    )
                )
                .order_by(SignalEvent.timestamp.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching signals for {employee_id}: {e}")
            return []
    
    async def _get_baseline(
        self,
        employee_id: str,
        db: AsyncSession
    ) -> Dict[str, BaselineProfile]:
        """Get baseline profiles for employee"""
        try:
            result = await db.execute(
                select(BaselineProfile)
                .where(BaselineProfile.employee_id == uuid.UUID(employee_id))
            )
            profiles = result.scalars().all()
            return {profile.metric: profile for profile in profiles}
        except Exception as e:
            logger.error(f"Error fetching baseline for {employee_id}: {e}")
            return {}
    
    # ========================================================================
    # OUTCOME RELIABILITY CALCULATION (35%)
    # ========================================================================
    
    async def _calc_outcome_score(
        self,
        signals: List[SignalEvent],
        db: AsyncSession
    ) -> float:
        """
        Calculate Outcome Reliability Score (0-100)
        
        Components:
        - Task Completion Rate (40%): % of tasks completed
        - Quality Score (35%): 1 - (defects/tasks)
        - Deadline Adherence (25%): % of tasks on time
        
        Formula: (completion × 0.40 + quality × 0.35 + deadline × 0.25) × 100
        """
        task_signals = [s for s in signals if s.signal_type in ['task_created', 'task_completed']]
        
        if not task_signals:
            return 50.0  # Default neutral score
        
        # Group tasks by metadata task_id
        tasks = defaultdict(dict)
        for signal in task_signals:
            task_id = signal.metadata.get('task_id')
            if task_id:
                if signal.signal_type == 'task_created':
                    tasks[task_id]['created'] = signal
                elif signal.signal_type == 'task_completed':
                    tasks[task_id]['completed'] = signal
        
        if not tasks:
            return 50.0
        
        # Calculate completion rate
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks.values() if 'completed' in t)
        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
        
        # Calculate quality score (based on defects/issues)
        defect_count = sum(
            1 for t in tasks.values() 
            if t.get('completed', {}).metadata.get('has_defects', False)
        )
        quality_score = 1.0 - (defect_count / completed_tasks if completed_tasks > 0 else 0.0)
        
        # Calculate deadline adherence
        on_time_count = sum(
            1 for t in tasks.values()
            if t.get('completed', {}).metadata.get('on_time', True)
        )
        deadline_adherence = on_time_count / completed_tasks if completed_tasks > 0 else 0.0
        
        # Combine with weights
        outcome_score = (
            completion_rate * self.OUTCOME_WEIGHTS['completion'] +
            quality_score * self.OUTCOME_WEIGHTS['quality'] +
            deadline_adherence * self.OUTCOME_WEIGHTS['deadline']
        ) * 100
        
        logger.debug(
            f"Outcome: completion={completion_rate:.2f}, quality={quality_score:.2f}, "
            f"deadline={deadline_adherence:.2f}, score={outcome_score:.2f}"
        )
        
        return outcome_score
    
    # ========================================================================
    # BEHAVIORAL CONSISTENCY CALCULATION (30%)
    # ========================================================================
    
    async def _calc_behavioral_score(
        self,
        signals: List[SignalEvent],
        baseline: Dict[str, BaselineProfile],
        db: AsyncSession
    ) -> float:
        """
        Calculate Behavioral Consistency Score (0-100)
        
        Components:
        - Pattern Deviation (30%): Z-score of daily patterns vs baseline
        - Response Time Consistency (25%): How close to baseline
        - Collaboration Score (20%): % of meetings attended, team interactions
        - Browsing Productivity (25%): Productive vs non-productive browsing
        
        Formula: ((1 - deviation) × 0.30 + response × 0.25 + collab × 0.20 + browsing × 0.25) × 100
        """
        # Calculate pattern deviation
        pattern_deviation = self._calc_pattern_deviation(signals, baseline)
        pattern_score = max(0.0, 1.0 - min(pattern_deviation, 1.0))
        
        # Calculate response time consistency
        response_score = self._calc_response_consistency(signals, baseline)
        
        # Calculate collaboration score
        collaboration_score = self._calc_collaboration(signals)
        
        # Calculate browsing productivity (NEW)
        browsing_score = await self._calc_browsing_productivity(signals, baseline, db)
        
        # Combine with weights
        behavioral_score = (
            pattern_score * self.BEHAVIORAL_WEIGHTS['pattern_deviation'] +
            response_score * self.BEHAVIORAL_WEIGHTS['response_time'] +
            collaboration_score * self.BEHAVIORAL_WEIGHTS['collaboration'] +
            browsing_score * self.BEHAVIORAL_WEIGHTS['browsing_productivity']
        ) * 100
        
        logger.debug(
            f"Behavioral: pattern={pattern_score:.2f}, response={response_score:.2f}, "
            f"collab={collaboration_score:.2f}, browsing={browsing_score:.2f}, score={behavioral_score:.2f}"
        )
        
        return behavioral_score
    
    def _calc_pattern_deviation(
        self,
        signals: List[SignalEvent],
        baseline: Dict[str, BaselineProfile]
    ) -> float:
        """Calculate pattern deviation from baseline (returns 0-1, lower is better)"""
        if not baseline:
            return 0.5  # Neutral
        
        # Calculate current metrics
        current_metrics = self._extract_current_metrics(signals)
        
        # Calculate Z-scores for each metric
        z_scores = []
        for metric_name, current_value in current_metrics.items():
            if metric_name in baseline:
                profile = baseline[metric_name]
                if profile.std_dev > 0:
                    z_score = abs(current_value - profile.baseline_value) / profile.std_dev
                    z_scores.append(min(z_score, 3.0))  # Cap at 3 std devs
        
        if not z_scores:
            return 0.5
        
        # Average Z-score normalized to 0-1 (3 std devs = 1.0)
        avg_z_score = np.mean(z_scores) / 3.0
        return min(avg_z_score, 1.0)
    
    def _calc_response_consistency(
        self,
        signals: List[SignalEvent],
        baseline: Dict[str, BaselineProfile]
    ) -> float:
        """Calculate response time consistency (returns 0-1)"""
        email_signals = [s for s in signals if s.signal_type in ['email_sent', 'email_received']]
        
        if not email_signals or 'email_response_time_minutes' not in baseline:
            return 0.5  # Neutral
        
        # Calculate current average response time
        response_times = [
            s.metadata.get('response_time_minutes', 0)
            for s in email_signals
            if s.metadata.get('response_time_minutes')
        ]
        
        if not response_times:
            return 0.5
        
        current_avg = np.mean(response_times)
        baseline_profile = baseline['email_response_time_minutes']
        
        # Calculate how close to baseline (within 1 std dev = 1.0, beyond 3 std devs = 0.0)
        if baseline_profile.std_dev > 0:
            deviation = abs(current_avg - baseline_profile.baseline_value) / baseline_profile.std_dev
            consistency = max(0.0, 1.0 - (deviation / 3.0))
        else:
            consistency = 1.0 if current_avg == baseline_profile.baseline_value else 0.5
        
        return consistency
    
    def _calc_collaboration(self, signals: List[SignalEvent]) -> float:
        """Calculate collaboration score (returns 0-1)"""
        meeting_signals = [s for s in signals if s.signal_type == 'meeting_attended']
        
        if not meeting_signals:
            return 0.5  # Neutral
        
        # Calculate meeting attendance rate
        total_meetings = len([s for s in signals if s.signal_type == 'calendar_event'])
        attended_meetings = len(meeting_signals)
        
        if total_meetings == 0:
            return 0.5
        
        attendance_rate = attended_meetings / total_meetings
        
        # Bonus for active participation (based on metadata)
        active_participation = sum(
            1 for s in meeting_signals
            if s.metadata.get('participated', False)
        )
        participation_rate = active_participation / attended_meetings if attended_meetings > 0 else 0.0
        
        # Combine attendance and participation
        collaboration_score = (attendance_rate * 0.6 + participation_rate * 0.4)
        
        return collaboration_score
    
    async def _calc_browsing_productivity(
        self,
        signals: List[SignalEvent],
        baseline: Dict[str, BaselineProfile],
        db: AsyncSession
    ) -> float:
        """
        Calculate browsing productivity score (returns 0-1)
        
        Based on:
        - Time spent on productive vs non-productive websites
        - Browsing during work hours vs off-hours
        - Deviation from baseline browsing patterns
        
        Formula: (productive_ratio × 0.5 + work_hours_ratio × 0.3 + pattern_consistency × 0.2)
        """
        try:
            # Get employee ID from signals
            if not signals:
                return 0.5  # Neutral
            
            employee_id = str(signals[0].employee_id)
            
            # Check if employee has consented to traffic monitoring
            consent_check = await db.execute(
                text('''
                    SELECT consented FROM traffic_monitoring_consent
                    WHERE employee_id = :employee_id
                    AND consented = TRUE
                    AND withdrawn_date IS NULL
                '''),
                {'employee_id': employee_id}
            )
            consent = consent_check.scalar()
            
            if not consent:
                return 0.5  # No consent = neutral score (don't penalize)
            
            # Get browsing data from last 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=self.window_days)
            
            browsing_data = await db.execute(
                text('''
                    SELECT 
                        SUM(CASE WHEN productivity_score >= 70 THEN visit_duration_seconds ELSE 0 END) as productive_seconds,
                        SUM(CASE WHEN productivity_score < 70 THEN visit_duration_seconds ELSE 0 END) as unproductive_seconds,
                        SUM(visit_duration_seconds) as total_seconds,
                        COUNT(*) as visit_count,
                        AVG(productivity_score) as avg_productivity
                    FROM traffic_website_visits
                    WHERE employee_id = :employee_id
                    AND first_visit >= :cutoff_date
                '''),
                {'employee_id': employee_id, 'cutoff_date': cutoff_date}
            )
            
            result = browsing_data.fetchone()
            
            if not result or not result.total_seconds or result.total_seconds == 0:
                return 0.5  # No browsing data = neutral
            
            productive_seconds = result.productive_seconds or 0
            total_seconds = result.total_seconds or 1
            
            # Calculate productive browsing ratio
            productive_ratio = productive_seconds / total_seconds
            
            # Calculate work hours browsing ratio
            # (This would require time-of-day analysis, simplified here)
            work_hours_ratio = 0.7  # Placeholder - assume 70% during work hours
            
            # Calculate pattern consistency (compare to baseline)
            pattern_consistency = 0.5  # Default neutral
            if 'avg_productive_hours_per_day' in baseline:
                baseline_productive = baseline['avg_productive_hours_per_day'].baseline_value
                current_productive = productive_seconds / 3600 / self.window_days
                
                if baseline['avg_productive_hours_per_day'].std_dev > 0:
                    deviation = abs(current_productive - baseline_productive) / baseline['avg_productive_hours_per_day'].std_dev
                    pattern_consistency = max(0.0, 1.0 - (deviation / 3.0))  # Within 3 std devs
            
            # Combine components
            browsing_score = (
                productive_ratio * 0.5 +
                work_hours_ratio * 0.3 +
                pattern_consistency * 0.2
            )
            
            logger.debug(
                f"Browsing productivity: productive_ratio={productive_ratio:.2f}, "
                f"work_hours={work_hours_ratio:.2f}, pattern={pattern_consistency:.2f}, "
                f"score={browsing_score:.2f}"
            )
            
            return min(1.0, max(0.0, browsing_score))
        
        except Exception as e:
            logger.error(f"Error calculating browsing productivity: {e}")
            return 0.5  # Neutral on error
    
    def _extract_current_metrics(self, signals: List[SignalEvent]) -> Dict[str, float]:
        """Extract current metric values from signals"""
        metrics = {}
        
        # Group signals by day
        daily_signals = defaultdict(list)
        for signal in signals:
            day = signal.timestamp.date()
            daily_signals[day].append(signal)
        
        num_days = len(daily_signals)
        if num_days == 0:
            return metrics
        
        # Meetings per day
        meeting_counts = [
            len([s for s in day_signals if s.signal_type == 'meeting_attended'])
            for day_signals in daily_signals.values()
        ]
        if meeting_counts:
            metrics['meetings_per_day'] = np.mean(meeting_counts)
        
        # Email response time
        response_times = [
            s.metadata.get('response_time_minutes', 0)
            for s in signals
            if s.signal_type == 'email_sent' and s.metadata.get('response_time_minutes')
        ]
        if response_times:
            metrics['email_response_time_minutes'] = np.mean(response_times)
        
        # Task completion rate
        task_created = len([s for s in signals if s.signal_type == 'task_created'])
        task_completed = len([s for s in signals if s.signal_type == 'task_completed'])
        if task_created > 0:
            metrics['task_completion_rate'] = task_completed / task_created
        
        return metrics
    
    # ========================================================================
    # SECURITY HYGIENE CALCULATION (20%)
    # ========================================================================
    
    async def _calc_security_score(
        self,
        signals: List[SignalEvent],
        baseline: Dict[str, BaselineProfile],
        db: AsyncSession
    ) -> float:
        """
        Calculate Security Hygiene Score (0-100)
        
        Components:
        - MFA Enabled (33%): Yes/No
        - VPN Compliance (33%): % of time connected when accessing sensitive data
        - Phishing Safety (34%): 1 - (phishing incidents/emails)
        
        Formula: (mfa × 0.33 + vpn × 0.33 + phishing × 0.34) × 100
        """
        # Check MFA status (from metadata)
        mfa_enabled = any(
            s.metadata.get('mfa_enabled', False)
            for s in signals
        )
        mfa_score = 1.0 if mfa_enabled else 0.0
        
        # Calculate VPN compliance
        vpn_score = self._calc_vpn_compliance(signals)
        
        # Calculate phishing safety
        phishing_score = self._calc_phishing_safety(signals)
        
        # Combine with weights
        security_score = (
            mfa_score * self.SECURITY_WEIGHTS['mfa'] +
            vpn_score * self.SECURITY_WEIGHTS['vpn'] +
            phishing_score * self.SECURITY_WEIGHTS['phishing']
        ) * 100
        
        logger.debug(
            f"Security: mfa={mfa_score:.2f}, vpn={vpn_score:.2f}, "
            f"phishing={phishing_score:.2f}, score={security_score:.2f}"
        )
        
        return security_score
    
    def _calc_vpn_compliance(self, signals: List[SignalEvent]) -> float:
        """Calculate VPN compliance score (returns 0-1)"""
        # Count sensitive data access events
        sensitive_access = [
            s for s in signals
            if s.metadata.get('sensitive_data_access', False)
        ]
        
        if not sensitive_access:
            return 1.0  # No sensitive access = compliant
        
        # Count how many had VPN enabled
        vpn_protected = sum(
            1 for s in sensitive_access
            if s.metadata.get('vpn_connected', False)
        )
        
        compliance_rate = vpn_protected / len(sensitive_access)
        return compliance_rate
    
    def _calc_phishing_safety(self, signals: List[SignalEvent]) -> float:
        """Calculate phishing safety score (returns 0-1)"""
        email_signals = [s for s in signals if s.signal_type in ['email_sent', 'email_received']]
        
        if not email_signals:
            return 1.0  # No emails = safe
        
        # Count phishing incidents
        phishing_incidents = sum(
            1 for s in email_signals
            if s.metadata.get('phishing_detected', False) or s.metadata.get('clicked_phishing', False)
        )
        
        # Safety score: 1 - (incidents / total emails)
        safety_score = 1.0 - (phishing_incidents / len(email_signals))
        return max(0.0, safety_score)
    
    # ========================================================================
    # PSYCHOLOGICAL WELLBEING CALCULATION (15%)
    # ========================================================================
    
    async def _calc_wellbeing_score(
        self,
        signals: List[SignalEvent],
        db: AsyncSession
    ) -> float:
        """
        Calculate Psychological Wellbeing Score (0-100)
        
        Components:
        - Engagement Score (35%): Work quality, enthusiasm signals
        - Stress Level (40%): 1 - (stress indicators/total hours)
        - Sentiment Score (25%): Email sentiment analysis
        
        Formula: (engagement × 0.35 + (1-stress) × 0.40 + sentiment × 0.25) × 100
        """
        # Calculate engagement
        engagement_score = self._calc_engagement(signals)
        
        # Calculate stress level (inverted: lower stress = higher score)
        stress_level = self._calc_stress(signals)
        stress_score = 1.0 - stress_level
        
        # Calculate sentiment
        sentiment_score = self._calc_sentiment(signals)
        
        # Combine with weights
        wellbeing_score = (
            engagement_score * self.WELLBEING_WEIGHTS['engagement'] +
            stress_score * self.WELLBEING_WEIGHTS['stress'] +
            sentiment_score * self.WELLBEING_WEIGHTS['sentiment']
        ) * 100
        
        logger.debug(
            f"Wellbeing: engagement={engagement_score:.2f}, stress={stress_score:.2f}, "
            f"sentiment={sentiment_score:.2f}, score={wellbeing_score:.2f}"
        )
        
        return wellbeing_score
    
    def _calc_engagement(self, signals: List[SignalEvent]) -> float:
        """Calculate engagement score (returns 0-1)"""
        # Engagement indicators
        engagement_signals = [
            s for s in signals
            if s.signal_type in ['code_commit', 'document_created', 'document_edited', 'task_completed']
        ]
        
        if not signals:
            return 0.5
        
        # Engagement rate: productive signals / total signals
        engagement_rate = len(engagement_signals) / len(signals)
        
        # Quality bonus: check for high-quality work indicators
        quality_bonus = sum(
            1 for s in engagement_signals
            if s.metadata.get('high_quality', False) or s.metadata.get('innovative', False)
        ) / len(engagement_signals) if engagement_signals else 0.0
        
        # Combine rate and quality
        engagement_score = (engagement_rate * 0.7 + quality_bonus * 0.3)
        
        return min(1.0, engagement_score)
    
    def _calc_stress(self, signals: List[SignalEvent]) -> float:
        """Calculate stress level (returns 0-1, higher = more stress)"""
        # Group by day to calculate daily hours
        daily_signals = defaultdict(list)
        for signal in signals:
            day = signal.timestamp.date()
            daily_signals[day].append(signal)
        
        if not daily_signals:
            return 0.5
        
        stress_indicators = 0
        total_days = len(daily_signals)
        
        for day, day_signals in daily_signals.items():
            # Calculate work hours for the day
            if day_signals:
                timestamps = [s.timestamp for s in day_signals]
                work_start = min(timestamps)
                work_end = max(timestamps)
                work_hours = (work_end - work_start).total_seconds() / 3600
                
                # Stress indicators
                if work_hours > 10:  # Long work day
                    stress_indicators += 1
                
                if work_start.hour < 7 or work_end.hour > 20:  # Odd hours
                    stress_indicators += 0.5
                
                # Check for weekend work
                if work_start.weekday() >= 5:  # Saturday or Sunday
                    stress_indicators += 0.5
        
        # Normalize stress level
        stress_level = stress_indicators / total_days if total_days > 0 else 0.0
        return min(1.0, stress_level)
    
    def _calc_sentiment(self, signals: List[SignalEvent]) -> float:
        """Calculate sentiment score from communications (returns 0-1)"""
        email_signals = [s for s in signals if s.signal_type in ['email_sent', 'email_received']]
        
        if not email_signals:
            return 0.5  # Neutral
        
        # Extract sentiment scores from metadata
        sentiments = [
            s.metadata.get('sentiment_score', 0.5)
            for s in email_signals
            if 'sentiment_score' in s.metadata
        ]
        
        if not sentiments:
            return 0.5
        
        # Average sentiment (assuming 0-1 scale where 0.5 is neutral)
        avg_sentiment = np.mean(sentiments)
        
        return avg_sentiment
    
    # ========================================================================
    # TIME DECAY CALCULATION
    # ========================================================================
    
    def _calculate_time_decay(self, signals: List[SignalEvent]) -> float:
        """
        Apply time decay to recent events
        
        Time decay factors:
        - 0-7 days: 100% weight
        - 8-14 days: 80% weight
        - 15-30 days: 60% weight
        - 30+ days: 0% weight (ignored)
        
        Returns:
            Weighted average decay factor (0-1)
        """
        if not signals:
            return 1.0
        
        now = datetime.utcnow()
        weighted_sum = 0.0
        total_weight = 0.0
        
        for signal in signals:
            days_old = (now - signal.timestamp).days
            
            # Determine weight based on age
            weight = 0.0
            for (min_days, max_days), decay_factor in self.TIME_DECAY.items():
                if min_days <= days_old <= max_days:
                    weight = decay_factor
                    break
            
            weighted_sum += weight
            total_weight += 1.0
        
        decay_factor = weighted_sum / total_weight if total_weight > 0 else 1.0
        
        logger.debug(f"Time decay factor: {decay_factor:.3f} (based on {len(signals)} signals)")
        
        return decay_factor
    
    # ========================================================================
    # STORAGE
    # ========================================================================
    
    async def _store_score(
        self,
        employee_id: str,
        scores: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """
        Store trust score in PostgreSQL
        
        Uses INSERT to create new score record
        """
        try:
            # Calculate expiration (30 days from now)
            expires_at = datetime.utcnow() + timedelta(days=30)
            
            trust_score = TrustScore(
                id=uuid.uuid4(),
                employee_id=uuid.UUID(employee_id),
                outcome_score=scores['outcome'],
                behavioral_score=scores['behavioral'],
                security_score=scores['security'],
                wellbeing_score=scores['wellbeing'],
                total_score=scores['total'],
                weights=self.WEIGHTS,
                timestamp=scores['timestamp'],
                calculated_at=datetime.utcnow(),
                expires_at=expires_at
            )
            
            db.add(trust_score)
            await db.flush()
            
            logger.debug(f"Stored trust score for employee {employee_id}")
            
        except Exception as e:
            logger.error(f"Error storing trust score for {employee_id}: {e}")
            raise


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point for trust score calculation"""
    logger.info("=" * 80)
    logger.info("TBAPS Trust Score Calculator - Daily Run")
    logger.info("=" * 80)
    
    calculator = TrustCalculator(window_days=30)
    
    try:
        summary = await calculator.calculate_daily_scores()
        
        logger.info("=" * 80)
        logger.info("Trust Score Calculation Summary:")
        logger.info(f"  Total Employees: {summary['total_employees']}")
        logger.info(f"  Successful: {summary['successful']}")
        logger.info(f"  Failed: {summary['failed']}")
        logger.info(f"  Duration: {summary['duration_seconds']:.2f}s")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Trust calculation failed: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
