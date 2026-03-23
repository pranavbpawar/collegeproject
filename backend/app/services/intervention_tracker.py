"""
TBAPS Intervention Tracking System

Tracks intervention recommendations, implementation, and outcomes.
Provides success metrics and ROI analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid
import json
from enum import Enum

from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.core.database import Base, get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InterventionStatus(str, Enum):
    """Intervention status"""
    RECOMMENDED = 'recommended'
    PLANNED = 'planned'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    DEFERRED = 'deferred'


class InterventionOutcome(str, Enum):
    """Intervention outcome"""
    SUCCESSFUL = 'successful'
    PARTIALLY_SUCCESSFUL = 'partially_successful'
    NOT_SUCCESSFUL = 'not_successful'
    TOO_EARLY = 'too_early_to_tell'


class Intervention(Base):
    """
    Intervention tracking model
    
    Stores intervention recommendations and tracks their implementation.
    """
    __tablename__ = 'interventions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Intervention details
    category = Column(String(50), nullable=False, index=True)  # wellness, performance, etc.
    priority = Column(String(20), nullable=False, index=True)  # critical, high, medium, low
    scope = Column(String(20), nullable=False)  # individual, team
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    actions = Column(JSON)  # List of recommended actions
    
    # Timeline
    recommended_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    urgency_days = Column(Integer, nullable=False)
    due_date = Column(DateTime, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Status tracking
    status = Column(String(20), nullable=False, default=InterventionStatus.RECOMMENDED)
    outcome = Column(String(30))
    
    # Metrics
    initial_metrics = Column(JSON)  # Baseline metrics when recommended
    final_metrics = Column(JSON)  # Metrics after intervention
    success_score = Column(Float)  # 0-1 score of intervention success
    
    # Implementation details
    assigned_to = Column(String(255))  # Manager or HR person responsible
    notes = Column(Text)
    completion_notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterventionTracker:
    """
    Intervention tracking and analytics system
    
    Tracks:
    - Intervention recommendations
    - Implementation progress
    - Outcomes and success rates
    - ROI and impact analysis
    """
    
    def __init__(self, db_connection: Optional[AsyncSession] = None):
        """Initialize tracker"""
        self.conn = db_connection
        logger.info("InterventionTracker initialized")
    
    async def create_intervention(
        self,
        employee_id: str,
        category: str,
        priority: str,
        title: str,
        description: str,
        actions: List[str],
        urgency_days: int,
        initial_metrics: Optional[Dict[str, Any]] = None,
        assigned_to: Optional[str] = None,
    ) -> str:
        """
        Create new intervention recommendation
        
        Args:
            employee_id: Employee UUID
            category: Intervention category
            priority: Priority level
            title: Intervention title
            description: Description
            actions: List of recommended actions
            urgency_days: Days until due
            initial_metrics: Baseline metrics
            assigned_to: Person responsible
        
        Returns:
            Intervention ID
        """
        async for db in get_db():
            try:
                intervention = Intervention(
                    employee_id=uuid.UUID(employee_id),
                    category=category,
                    priority=priority,
                    scope='individual',
                    title=title,
                    description=description,
                    actions=actions,
                    urgency_days=urgency_days,
                    due_date=datetime.utcnow() + timedelta(days=urgency_days),
                    initial_metrics=initial_metrics or {},
                    assigned_to=assigned_to,
                    status=InterventionStatus.RECOMMENDED,
                )
                
                db.add(intervention)
                await db.commit()
                await db.refresh(intervention)
                
                logger.info(f"Created intervention {intervention.id} for employee {employee_id}")
                
                return str(intervention.id)
                
            except Exception as e:
                logger.error(f"Error creating intervention: {e}")
                await db.rollback()
                raise
    
    async def update_status(
        self,
        intervention_id: str,
        status: InterventionStatus,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Update intervention status
        
        Args:
            intervention_id: Intervention UUID
            status: New status
            notes: Optional notes
        
        Returns:
            Success boolean
        """
        async for db in get_db():
            try:
                result = await db.execute(
                    select(Intervention)
                    .where(Intervention.id == uuid.UUID(intervention_id))
                )
                intervention = result.scalar()
                
                if not intervention:
                    logger.error(f"Intervention {intervention_id} not found")
                    return False
                
                intervention.status = status
                
                if status == InterventionStatus.IN_PROGRESS and not intervention.started_at:
                    intervention.started_at = datetime.utcnow()
                
                if status == InterventionStatus.COMPLETED and not intervention.completed_at:
                    intervention.completed_at = datetime.utcnow()
                
                if notes:
                    intervention.notes = notes
                
                await db.commit()
                
                logger.info(f"Updated intervention {intervention_id} status to {status}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error updating intervention status: {e}")
                await db.rollback()
                return False
    
    async def complete_intervention(
        self,
        intervention_id: str,
        outcome: InterventionOutcome,
        final_metrics: Dict[str, Any],
        completion_notes: Optional[str] = None,
    ) -> bool:
        """
        Mark intervention as completed with outcome
        
        Args:
            intervention_id: Intervention UUID
            outcome: Intervention outcome
            final_metrics: Final metrics after intervention
            completion_notes: Notes about completion
        
        Returns:
            Success boolean
        """
        async for db in get_db():
            try:
                result = await db.execute(
                    select(Intervention)
                    .where(Intervention.id == uuid.UUID(intervention_id))
                )
                intervention = result.scalar()
                
                if not intervention:
                    return False
                
                intervention.status = InterventionStatus.COMPLETED
                intervention.completed_at = datetime.utcnow()
                intervention.outcome = outcome
                intervention.final_metrics = final_metrics
                intervention.completion_notes = completion_notes
                
                # Calculate success score
                intervention.success_score = self._calculate_success_score(
                    intervention.category,
                    intervention.initial_metrics,
                    final_metrics,
                    outcome
                )
                
                await db.commit()
                
                logger.info(f"Completed intervention {intervention_id} with outcome {outcome}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error completing intervention: {e}")
                await db.rollback()
                return False
    
    async def get_employee_interventions(
        self,
        employee_id: str,
        status: Optional[InterventionStatus] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get interventions for employee
        
        Args:
            employee_id: Employee UUID
            status: Optional status filter
        
        Returns:
            List of interventions
        """
        async for db in get_db():
            try:
                query = select(Intervention).where(
                    Intervention.employee_id == uuid.UUID(employee_id)
                )
                
                if status:
                    query = query.where(Intervention.status == status)
                
                query = query.order_by(Intervention.recommended_at.desc())
                
                result = await db.execute(query)
                interventions = result.scalars().all()
                
                return [self._intervention_to_dict(i) for i in interventions]
                
            except Exception as e:
                logger.error(f"Error fetching interventions: {e}")
                return []
    
    async def get_overdue_interventions(self) -> List[Dict[str, Any]]:
        """Get all overdue interventions"""
        async for db in get_db():
            try:
                result = await db.execute(
                    select(Intervention)
                    .where(
                        and_(
                            Intervention.due_date < datetime.utcnow(),
                            Intervention.status.in_([
                                InterventionStatus.RECOMMENDED,
                                InterventionStatus.PLANNED,
                                InterventionStatus.IN_PROGRESS,
                            ])
                        )
                    )
                    .order_by(Intervention.due_date)
                )
                interventions = result.scalars().all()
                
                return [self._intervention_to_dict(i) for i in interventions]
                
            except Exception as e:
                logger.error(f"Error fetching overdue interventions: {e}")
                return []
    
    async def get_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get intervention analytics
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            Analytics dictionary
        """
        async for db in get_db():
            try:
                # Build query
                query = select(Intervention)
                
                if start_date:
                    query = query.where(Intervention.recommended_at >= start_date)
                if end_date:
                    query = query.where(Intervention.recommended_at <= end_date)
                
                result = await db.execute(query)
                interventions = result.scalars().all()
                
                # Calculate analytics
                total = len(interventions)
                
                if total == 0:
                    return {
                        'total_interventions': 0,
                        'by_status': {},
                        'by_category': {},
                        'by_priority': {},
                        'by_outcome': {},
                        'success_rate': 0.0,
                        'avg_completion_time_days': 0.0,
                    }
                
                # Group by status
                by_status = {}
                for i in interventions:
                    by_status[i.status] = by_status.get(i.status, 0) + 1
                
                # Group by category
                by_category = {}
                for i in interventions:
                    by_category[i.category] = by_category.get(i.category, 0) + 1
                
                # Group by priority
                by_priority = {}
                for i in interventions:
                    by_priority[i.priority] = by_priority.get(i.priority, 0) + 1
                
                # Group by outcome
                by_outcome = {}
                for i in interventions:
                    if i.outcome:
                        by_outcome[i.outcome] = by_outcome.get(i.outcome, 0) + 1
                
                # Calculate success rate
                completed = [i for i in interventions if i.status == InterventionStatus.COMPLETED]
                successful = [
                    i for i in completed
                    if i.outcome == InterventionOutcome.SUCCESSFUL
                ]
                success_rate = len(successful) / len(completed) if completed else 0.0
                
                # Calculate average completion time
                completion_times = []
                for i in completed:
                    if i.completed_at and i.recommended_at:
                        days = (i.completed_at - i.recommended_at).days
                        completion_times.append(days)
                
                avg_completion_time = (
                    sum(completion_times) / len(completion_times)
                    if completion_times else 0.0
                )
                
                return {
                    'total_interventions': total,
                    'by_status': by_status,
                    'by_category': by_category,
                    'by_priority': by_priority,
                    'by_outcome': by_outcome,
                    'success_rate': success_rate,
                    'avg_completion_time_days': avg_completion_time,
                    'completed_count': len(completed),
                    'successful_count': len(successful),
                }
                
            except Exception as e:
                logger.error(f"Error calculating analytics: {e}")
                return {}
    
    def _calculate_success_score(
        self,
        category: str,
        initial_metrics: Dict[str, Any],
        final_metrics: Dict[str, Any],
        outcome: InterventionOutcome,
    ) -> float:
        """
        Calculate success score for intervention
        
        Args:
            category: Intervention category
            initial_metrics: Initial metrics
            final_metrics: Final metrics
            outcome: Intervention outcome
        
        Returns:
            Success score (0-1)
        """
        # Base score from outcome
        outcome_scores = {
            InterventionOutcome.SUCCESSFUL: 1.0,
            InterventionOutcome.PARTIALLY_SUCCESSFUL: 0.6,
            InterventionOutcome.NOT_SUCCESSFUL: 0.2,
            InterventionOutcome.TOO_EARLY: 0.5,
        }
        
        base_score = outcome_scores.get(outcome, 0.5)
        
        # Adjust based on metrics improvement
        if category == 'wellness' and 'burnout_risk' in initial_metrics and 'burnout_risk' in final_metrics:
            improvement = initial_metrics['burnout_risk'] - final_metrics['burnout_risk']
            if improvement > 0.2:
                base_score = min(1.0, base_score + 0.2)
        
        elif category == 'performance' and 'performance_trend' in initial_metrics and 'performance_trend' in final_metrics:
            improvement = final_metrics['performance_trend'] - initial_metrics['performance_trend']
            if improvement > 0.1:
                base_score = min(1.0, base_score + 0.2)
        
        elif category == 'engagement' and 'trust_score' in initial_metrics and 'trust_score' in final_metrics:
            improvement = final_metrics['trust_score'] - initial_metrics['trust_score']
            if improvement > 10:
                base_score = min(1.0, base_score + 0.2)
        
        return base_score
    
    def _intervention_to_dict(self, intervention: Intervention) -> Dict[str, Any]:
        """Convert intervention model to dictionary"""
        return {
            'id': str(intervention.id),
            'employee_id': str(intervention.employee_id),
            'category': intervention.category,
            'priority': intervention.priority,
            'scope': intervention.scope,
            'title': intervention.title,
            'description': intervention.description,
            'actions': intervention.actions,
            'recommended_at': intervention.recommended_at.isoformat() if intervention.recommended_at else None,
            'urgency_days': intervention.urgency_days,
            'due_date': intervention.due_date.isoformat() if intervention.due_date else None,
            'started_at': intervention.started_at.isoformat() if intervention.started_at else None,
            'completed_at': intervention.completed_at.isoformat() if intervention.completed_at else None,
            'status': intervention.status,
            'outcome': intervention.outcome,
            'initial_metrics': intervention.initial_metrics,
            'final_metrics': intervention.final_metrics,
            'success_score': intervention.success_score,
            'assigned_to': intervention.assigned_to,
            'notes': intervention.notes,
            'completion_notes': intervention.completion_notes,
        }
