"""
TBAPS Traffic Monitoring API Endpoints

Provides REST API for accessing employee browsing data
GDPR-compliant with consent checks and audit logging
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.core.auth import get_current_user
from pydantic import BaseModel, Field

router = APIRouter(prefix="/traffic", tags=["traffic"])


# ============================================================================
# SCHEMAS
# ============================================================================

class ConsentRequest(BaseModel):
    """Request to grant/withdraw traffic monitoring consent"""
    employee_id: str
    consented: bool
    consent_text: Optional[str] = None


class ConsentResponse(BaseModel):
    """Consent status response"""
    employee_id: str
    consented: bool
    consent_date: Optional[datetime]
    withdrawn_date: Optional[datetime]


class WebsiteVisit(BaseModel):
    """Website visit record"""
    domain: str
    category: str
    productivity_score: int
    first_visit: datetime
    last_visit: datetime
    visit_duration_seconds: int
    page_count: int


class BrowsingSummary(BaseModel):
    """Employee browsing summary"""
    employee_id: str
    total_visits: int
    unique_domains: int
    total_time_seconds: int
    productive_time_seconds: int
    avg_productivity_score: float
    top_domains: List[dict]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/consent", response_model=ConsentResponse)
async def manage_consent(
    request: ConsentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Grant or withdraw traffic monitoring consent
    
    **Privacy:** Employees must explicitly consent to traffic monitoring
    """
    try:
        # Check if consent record exists
        existing = await db.execute(
            text('''
                SELECT * FROM traffic_monitoring_consent
                WHERE employee_id = :employee_id
            '''),
            {'employee_id': request.employee_id}
        )
        existing_record = existing.fetchone()
        
        if existing_record:
            # Update existing consent
            if request.consented:
                await db.execute(
                    text('''
                        UPDATE traffic_monitoring_consent
                        SET consented = TRUE,
                            consent_date = NOW(),
                            withdrawn_date = NULL,
                            consent_text = :consent_text,
                            updated_at = NOW()
                        WHERE employee_id = :employee_id
                    '''),
                    {'employee_id': request.employee_id, 'consent_text': request.consent_text or 'Standard consent'}
                )
            else:
                await db.execute(
                    text('''
                        UPDATE traffic_monitoring_consent
                        SET consented = FALSE,
                            withdrawn_date = NOW(),
                            updated_at = NOW()
                        WHERE employee_id = :employee_id
                    '''),
                    {'employee_id': request.employee_id}
                )
        else:
            # Create new consent record
            await db.execute(
                text('''
                    INSERT INTO traffic_monitoring_consent (
                        employee_id, consented, consent_date, consent_text, consent_version
                    ) VALUES (:employee_id, :consented, NOW(), :consent_text, '1.0')
                '''),
                {
                    'employee_id': request.employee_id,
                    'consented': request.consented,
                    'consent_text': request.consent_text or 'Standard consent'
                }
            )
        
        # Log audit event
        await db.execute(
            text('''
                INSERT INTO traffic_audit_log (
                    action, actor_id, target_employee_id, details
                ) VALUES (:action, :actor_id, :target_id, :details)
            '''),
            {
                'action': 'consent_granted' if request.consented else 'consent_withdrawn',
                'actor_id': current_user.get('id', 'system'),
                'target_id': request.employee_id,
                'details': f'{{"consented": {request.consented}}}'
            }
        )
        
        await db.commit()
        
        # Return updated consent status
        result = await db.execute(
            text('''
                SELECT employee_id, consented, consent_date, withdrawn_date
                FROM traffic_monitoring_consent
                WHERE employee_id = :employee_id
            '''),
            {'employee_id': request.employee_id}
        )
        record = result.fetchone()
        
        return ConsentResponse(
            employee_id=record.employee_id,
            consented=record.consented,
            consent_date=record.consent_date,
            withdrawn_date=record.withdrawn_date
        )
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error managing consent: {str(e)}"
        )


@router.get("/employee/{employee_id}/summary", response_model=BrowsingSummary)
async def get_browsing_summary(
    employee_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get browsing summary for an employee
    
    **Privacy:** Requires active consent from employee
    **Authorization:** Managers can view their team, employees can view their own data
    """
    try:
        # Check consent
        consent_check = await db.execute(
            text('''
                SELECT consented FROM traffic_monitoring_consent
                WHERE employee_id = :employee_id
                AND consented = TRUE
                AND withdrawn_date IS NULL
            '''),
            {'employee_id': employee_id}
        )
        
        if not consent_check.scalar():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee has not consented to traffic monitoring"
            )
        
        # Log audit event
        await db.execute(
            text('''
                INSERT INTO traffic_audit_log (
                    action, actor_id, target_employee_id
                ) VALUES ('viewed_traffic', :actor_id, :target_id)
            '''),
            {'actor_id': current_user.get('id', 'unknown'), 'target_id': employee_id}
        )
        
        # Get browsing summary
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        summary = await db.execute(
            text('''
                SELECT 
                    COUNT(*) as total_visits,
                    COUNT(DISTINCT domain) as unique_domains,
                    SUM(visit_duration_seconds) as total_time_seconds,
                    SUM(CASE WHEN productivity_score >= 70 THEN visit_duration_seconds ELSE 0 END) as productive_time_seconds,
                    AVG(productivity_score) as avg_productivity_score
                FROM traffic_website_visits
                WHERE employee_id = :employee_id
                AND first_visit >= :cutoff_date
            '''),
            {'employee_id': employee_id, 'cutoff_date': cutoff_date}
        )
        
        result = summary.fetchone()
        
        # Get top domains
        top_domains = await db.execute(
            text('''
                SELECT 
                    domain,
                    category,
                    SUM(visit_duration_seconds) as total_seconds,
                    COUNT(*) as visit_count
                FROM traffic_website_visits
                WHERE employee_id = :employee_id
                AND first_visit >= :cutoff_date
                GROUP BY domain, category
                ORDER BY total_seconds DESC
                LIMIT 10
            '''),
            {'employee_id': employee_id, 'cutoff_date': cutoff_date}
        )
        
        top_domains_list = [
            {
                'domain': row.domain,
                'category': row.category,
                'total_seconds': row.total_seconds,
                'visit_count': row.visit_count
            }
            for row in top_domains.fetchall()
        ]
        
        await db.commit()
        
        return BrowsingSummary(
            employee_id=employee_id,
            total_visits=result.total_visits or 0,
            unique_domains=result.unique_domains or 0,
            total_time_seconds=result.total_time_seconds or 0,
            productive_time_seconds=result.productive_time_seconds or 0,
            avg_productivity_score=float(result.avg_productivity_score or 50.0),
            top_domains=top_domains_list
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching browsing summary: {str(e)}"
        )


@router.get("/employee/{employee_id}/websites", response_model=List[WebsiteVisit])
async def get_website_visits(
    employee_id: str,
    days: int = 7,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed website visits for an employee
    
    **Privacy:** Requires active consent
    """
    try:
        # Check consent
        consent_check = await db.execute(
            text('''
                SELECT consented FROM traffic_monitoring_consent
                WHERE employee_id = :employee_id
                AND consented = TRUE
                AND withdrawn_date IS NULL
            '''),
            {'employee_id': employee_id}
        )
        
        if not consent_check.scalar():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee has not consented to traffic monitoring"
            )
        
        # Get website visits
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        visits = await db.execute(
            text('''
                SELECT 
                    domain, category, productivity_score,
                    first_visit, last_visit, visit_duration_seconds, page_count
                FROM traffic_website_visits
                WHERE employee_id = :employee_id
                AND first_visit >= :cutoff_date
                ORDER BY first_visit DESC
                LIMIT :limit
            '''),
            {'employee_id': employee_id, 'cutoff_date': cutoff_date, 'limit': limit}
        )
        
        return [
            WebsiteVisit(
                domain=row.domain,
                category=row.category,
                productivity_score=row.productivity_score,
                first_visit=row.first_visit,
                last_visit=row.last_visit,
                visit_duration_seconds=row.visit_duration_seconds,
                page_count=row.page_count
            )
            for row in visits.fetchall()
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching website visits: {str(e)}"
        )


@router.get("/categories")
async def get_website_categories(
    db: AsyncSession = Depends(get_db)
):
    """Get all website categories and productivity scores"""
    try:
        categories = await db.execute(
            text('''
                SELECT domain_pattern, category, productivity_score, description
                FROM website_categories
                ORDER BY productivity_score DESC, domain_pattern
            ''')
        )
        
        return [
            {
                'domain_pattern': row.domain_pattern,
                'category': row.category,
                'productivity_score': row.productivity_score,
                'description': row.description
            }
            for row in categories.fetchall()
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching categories: {str(e)}"
        )
