"""
TBAPS Baseline Establishment Engine
Analyzes first 30 days of employee signals to create individual baseline profiles
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import uuid4
import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.models.employee import Employee
from app.models.signal_event import SignalEvent
from app.models.baseline_profile import BaselineProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/tbaps/baseline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BaselineEngine:
    """
    Baseline Establishment Engine
    
    Analyzes employee signal data over a 30-day period to establish
    statistical baselines for trust scoring and anomaly detection.
    """
    
    def __init__(self, min_days: int = 14, target_days: int = 30):
        """
        Initialize baseline engine
        
        Args:
            min_days: Minimum days of data required (default: 14)
            target_days: Target days for full baseline (default: 30)
        """
        self.min_days = min_days
        self.target_days = target_days
        self.min_confidence = 0.5
        self.logger = logger
    
    async def establish_all_baselines(self, days_lookback: int = 30) -> Dict[str, Any]:
        """
        Establish baselines for all active employees
        
        Args:
            days_lookback: Number of days to look back for signal data
        
        Returns:
            Summary statistics of baseline establishment
        """
        self.logger.info(f"Starting baseline establishment for all employees (lookback: {days_lookback} days)")
        
        summary = {
            'total_employees': 0,
            'successful': 0,
            'failed': 0,
            'insufficient_data': 0,
            'errors': [],
            'start_time': datetime.utcnow(),
        }
        
        async with AsyncSessionLocal() as db:
            try:
                # Get all active employees
                result = await db.execute(
                    select(Employee).where(
                        Employee.status == 'active',
                        Employee.deleted_at.is_(None)
                    )
                )
                employees = result.scalars().all()
                summary['total_employees'] = len(employees)
                
                self.logger.info(f"Found {len(employees)} active employees")
                
                # Process each employee
                for employee in employees:
                    try:
                        success = await self.establish_employee_baseline(
                            employee.id,
                            days_lookback,
                            db
                        )
                        
                        if success:
                            summary['successful'] += 1
                        else:
                            summary['insufficient_data'] += 1
                    
                    except Exception as e:
                        self.logger.error(f"Failed to establish baseline for employee {employee.id}: {e}")
                        summary['failed'] += 1
                        summary['errors'].append({
                            'employee_id': str(employee.id),
                            'error': str(e)
                        })
                
                await db.commit()
                
            except Exception as e:
                self.logger.error(f"Fatal error in baseline establishment: {e}")
                summary['errors'].append({'fatal_error': str(e)})
        
        summary['end_time'] = datetime.utcnow()
        summary['duration_seconds'] = (summary['end_time'] - summary['start_time']).total_seconds()
        
        self.logger.info(
            f"Baseline establishment complete: {summary['successful']} successful, "
            f"{summary['insufficient_data']} insufficient data, "
            f"{summary['failed']} failed, "
            f"Duration: {summary['duration_seconds']:.2f}s"
        )
        
        return summary
    
    async def establish_employee_baseline(
        self,
        employee_id: str,
        days_lookback: int = 30,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Establish baseline for a single employee
        
        Args:
            employee_id: Employee UUID
            days_lookback: Number of days to analyze
            db: Database session (optional)
        
        Returns:
            True if baseline established successfully, False if insufficient data
        """
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            self.logger.info(f"Establishing baseline for employee {employee_id}")
            
            # Get signal data
            cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)
            signals = await self._get_signals(employee_id, cutoff_date, db)
            
            # Check minimum data requirement
            unique_days = len(set(s.timestamp.date() for s in signals))
            if unique_days < self.min_days:
                self.logger.warning(
                    f"Insufficient data for employee {employee_id}: "
                    f"{unique_days} days (minimum: {self.min_days})"
                )
                return False
            
            self.logger.info(f"Processing {len(signals)} signals across {unique_days} days")
            
            # Extract and calculate metrics
            metrics = await self._extract_metrics(signals)
            
            # Calculate statistics for each metric
            for metric_name, values in metrics.items():
                if not values:
                    self.logger.debug(f"No data for metric {metric_name}")
                    continue
                
                stats = self._calculate_statistics(values)
                confidence = self._calculate_confidence(len(values), unique_days, days_lookback)
                
                # Store baseline
                await self._store_baseline(
                    employee_id,
                    metric_name,
                    stats,
                    confidence,
                    cutoff_date,
                    datetime.utcnow(),
                    db
                )
                
                self.logger.debug(
                    f"Stored baseline for {metric_name}: "
                    f"mean={stats['mean']:.2f}, std_dev={stats['std_dev']:.2f}, "
                    f"confidence={confidence:.2f}"
                )
            
            self.logger.info(f"Successfully established baseline for employee {employee_id}")
            return True
        
        finally:
            if should_close_db:
                await db.close()
    
    async def _get_signals(
        self,
        employee_id: str,
        cutoff_date: datetime,
        db: AsyncSession
    ) -> List[SignalEvent]:
        """Get signal events for employee within date range"""
        result = await db.execute(
            select(SignalEvent).where(
                and_(
                    SignalEvent.employee_id == employee_id,
                    SignalEvent.timestamp >= cutoff_date
                )
            ).order_by(SignalEvent.timestamp)
        )
        return result.scalars().all()
    
    async def _extract_metrics(self, signals: List[SignalEvent]) -> Dict[str, List[float]]:
        """
        Extract metrics from signal events
        
        Returns:
            Dictionary mapping metric names to lists of values
        """
        metrics = {
            'meetings_per_day': [],
            'email_response_time_minutes': [],
            'task_completion_rate': [],
            'work_hours_start': [],
            'work_hours_end': [],
            'context_switches_per_day': [],
            'collaboration_intensity': [],
            'average_meeting_duration_minutes': [],
            'emails_sent_per_day': [],
            'emails_received_per_day': [],
            'tasks_completed_per_day': [],
        }
        
        # Group signals by day
        signals_by_day = {}
        for signal in signals:
            day = signal.timestamp.date()
            if day not in signals_by_day:
                signals_by_day[day] = []
            signals_by_day[day].append(signal)
        
        # Calculate daily metrics
        for day, day_signals in signals_by_day.items():
            # Meetings per day
            meeting_count = sum(1 for s in day_signals if s.signal_type in ['calendar_event', 'meeting_attended'])
            metrics['meetings_per_day'].append(meeting_count)
            
            # Email response time (from metadata)
            email_response_times = [
                s.metadata.get('response_time_minutes', 0)
                for s in day_signals
                if s.signal_type == 'email_sent' and s.metadata.get('response_time_minutes')
            ]
            if email_response_times:
                metrics['email_response_time_minutes'].extend(email_response_times)
            
            # Task completion rate
            tasks_created = sum(1 for s in day_signals if s.signal_type == 'task_created')
            tasks_completed = sum(1 for s in day_signals if s.signal_type == 'task_completed')
            if tasks_created > 0:
                completion_rate = (tasks_completed / tasks_created) * 100
                metrics['task_completion_rate'].append(completion_rate)
            
            # Work hours
            timestamps = [s.timestamp for s in day_signals]
            if timestamps:
                # Start time (hour of day as float)
                start_time = min(timestamps).hour + min(timestamps).minute / 60
                metrics['work_hours_start'].append(start_time)
                
                # End time
                end_time = max(timestamps).hour + max(timestamps).minute / 60
                metrics['work_hours_end'].append(end_time)
            
            # Context switches (signal type changes)
            if len(day_signals) > 1:
                switches = sum(
                    1 for i in range(1, len(day_signals))
                    if day_signals[i].signal_type != day_signals[i-1].signal_type
                )
                metrics['context_switches_per_day'].append(switches)
            
            # Collaboration intensity (meetings + emails)
            collab_count = sum(
                1 for s in day_signals
                if s.signal_type in ['calendar_event', 'meeting_attended', 'email_sent', 'email_received']
            )
            metrics['collaboration_intensity'].append(collab_count)
            
            # Average meeting duration
            meeting_durations = [
                s.metadata.get('duration_minutes', 0)
                for s in day_signals
                if s.signal_type in ['calendar_event', 'meeting_attended']
                and s.metadata.get('duration_minutes')
            ]
            if meeting_durations:
                metrics['average_meeting_duration_minutes'].append(np.mean(meeting_durations))
            
            # Emails sent/received per day
            emails_sent = sum(1 for s in day_signals if s.signal_type == 'email_sent')
            emails_received = sum(1 for s in day_signals if s.signal_type == 'email_received')
            metrics['emails_sent_per_day'].append(emails_sent)
            metrics['emails_received_per_day'].append(emails_received)
            
            # Tasks completed per day
            metrics['tasks_completed_per_day'].append(tasks_completed)
        
        # Filter out empty metrics
        return {k: v for k, v in metrics.items() if v}
    
    def _calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """
        Calculate comprehensive statistics for a metric
        
        Args:
            values: List of metric values
        
        Returns:
            Dictionary of statistical measures
        """
        if not values:
            return {}
        
        values_array = np.array(values)
        
        # Handle edge cases
        if len(values) == 1:
            single_value = float(values[0])
            return {
                'mean': single_value,
                'median': single_value,
                'std_dev': 0.0,
                'p05': single_value,
                'p25': single_value,
                'p50': single_value,
                'p75': single_value,
                'p95': single_value,
                'min_value': single_value,
                'max_value': single_value,
                'sample_size': 1
            }
        
        return {
            'mean': float(np.mean(values_array)),
            'median': float(np.median(values_array)),
            'std_dev': float(np.std(values_array, ddof=1)),  # Sample std dev
            'p05': float(np.percentile(values_array, 5)),
            'p25': float(np.percentile(values_array, 25)),
            'p50': float(np.percentile(values_array, 50)),
            'p75': float(np.percentile(values_array, 75)),
            'p95': float(np.percentile(values_array, 95)),
            'min_value': float(np.min(values_array)),
            'max_value': float(np.max(values_array)),
            'sample_size': len(values)
        }
    
    def _calculate_confidence(
        self,
        data_points: int,
        unique_days: int,
        target_days: int
    ) -> float:
        """
        Calculate confidence score for baseline
        
        Confidence is based on:
        - Number of unique days with data
        - Number of data points
        
        Args:
            data_points: Total number of data points
            unique_days: Number of unique days with data
            target_days: Target number of days (30)
        
        Returns:
            Confidence score between 0.5 and 1.0
        """
        # Day coverage (0-1)
        day_coverage = min(1.0, unique_days / target_days)
        
        # Data density (expect at least 5 signals per day)
        expected_signals = target_days * 5
        data_density = min(1.0, data_points / expected_signals)
        
        # Combined confidence (weighted average)
        confidence = (day_coverage * 0.7) + (data_density * 0.3)
        
        # Ensure minimum confidence
        return max(self.min_confidence, confidence)
    
    async def _store_baseline(
        self,
        employee_id: str,
        metric: str,
        stats: Dict[str, float],
        confidence: float,
        calculation_start: datetime,
        calculation_end: datetime,
        db: AsyncSession
    ) -> None:
        """
        Store baseline profile in database
        
        Uses INSERT ... ON CONFLICT to update existing baselines
        """
        expires_at = datetime.utcnow() + timedelta(days=90)
        
        stmt = insert(BaselineProfile).values(
            id=uuid4(),
            employee_id=employee_id,
            metric=metric,
            baseline_value=stats['mean'],
            std_dev=stats['std_dev'],
            p95=stats['p95'],
            p50=stats['p50'],
            p05=stats['p05'],
            min_value=stats['min_value'],
            max_value=stats['max_value'],
            confidence=confidence,
            sample_size=stats['sample_size'],
            calculation_start=calculation_start,
            calculation_end=calculation_end,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            expires_at=expires_at
        ).on_conflict_do_update(
            index_elements=['employee_id', 'metric'],
            set_={
                'baseline_value': stats['mean'],
                'std_dev': stats['std_dev'],
                'p95': stats['p95'],
                'p50': stats['p50'],
                'p05': stats['p05'],
                'min_value': stats['min_value'],
                'max_value': stats['max_value'],
                'confidence': confidence,
                'sample_size': stats['sample_size'],
                'calculation_start': calculation_start,
                'calculation_end': calculation_end,
                'updated_at': datetime.utcnow(),
                'expires_at': expires_at
            }
        )
        
        await db.execute(stmt)
    
    async def get_employee_baseline(
        self,
        employee_id: str,
        metric: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get baseline profile(s) for an employee
        
        Args:
            employee_id: Employee UUID
            metric: Specific metric name (optional, returns all if None)
        
        Returns:
            List of baseline profiles
        """
        async with AsyncSessionLocal() as db:
            query = select(BaselineProfile).where(
                BaselineProfile.employee_id == employee_id
            )
            
            if metric:
                query = query.where(BaselineProfile.metric == metric)
            
            result = await db.execute(query)
            baselines = result.scalars().all()
            
            return [
                {
                    'metric': b.metric,
                    'baseline_value': b.baseline_value,
                    'std_dev': b.std_dev,
                    'p95': b.p95,
                    'p50': b.p50,
                    'p05': b.p05,
                    'min_value': b.min_value,
                    'max_value': b.max_value,
                    'confidence': b.confidence,
                    'sample_size': b.sample_size,
                    'updated_at': b.updated_at
                }
                for b in baselines
            ]


async def main():
    """Main entry point for baseline establishment"""
    engine = BaselineEngine(min_days=14, target_days=30)
    summary = await engine.establish_all_baselines(days_lookback=30)
    
    logger.info("Baseline Establishment Summary:")
    logger.info(f"  Total employees: {summary['total_employees']}")
    logger.info(f"  Successful: {summary['successful']}")
    logger.info(f"  Insufficient data: {summary['insufficient_data']}")
    logger.info(f"  Failed: {summary['failed']}")
    logger.info(f"  Duration: {summary['duration_seconds']:.2f}s")
    
    if summary['errors']:
        logger.error(f"  Errors: {len(summary['errors'])}")
        for error in summary['errors'][:5]:  # Show first 5 errors
            logger.error(f"    {error}")


if __name__ == '__main__':
    asyncio.run(main())
