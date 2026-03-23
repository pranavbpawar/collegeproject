"""
Employee Copilot API Endpoints

Privacy-first AI assistant endpoints for employee insights and recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_employee
from app.services.employee_copilot import EmployeeCopilot
from app.models import Employee

router = APIRouter(prefix="/api/v1/copilot", tags=["Employee Copilot"])


@router.get("/insights")
async def get_insights(
    days: int = 30,
    current_employee: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized insights for current employee
    
    Privacy-first: Only returns data for the authenticated employee.
    
    Args:
        days: Number of days to analyze (default: 30, max: 90)
        current_employee: Authenticated employee
        db: Database session
    
    Returns:
        Personalized insights including:
        - Summary of performance
        - Achievements and wins
        - Focus areas
        - Personalized recommendations
        - Key metrics
        - Productivity patterns
        - Wellness insights
    """
    # Validate days parameter
    if days < 1 or days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 90"
        )
    
    try:
        copilot = EmployeeCopilot(db)
        insights = await copilot.get_personalized_insights(
            str(current_employee.id),
            days=days
        )
        
        return {
            'success': True,
            'data': insights,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating insights: {str(e)}"
        )


@router.get("/recommendations")
async def get_recommendations(
    current_employee: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized recommendations for current employee
    
    Returns actionable recommendations based on:
    - Productivity patterns
    - Work-life balance
    - Collaboration
    - Skill development
    
    Args:
        current_employee: Authenticated employee
        db: Database session
    
    Returns:
        List of personalized recommendations
    """
    try:
        copilot = EmployeeCopilot(db)
        
        # Get trends and challenges
        trends = await copilot.get_trends(str(current_employee.id), 30, db)
        challenges = await copilot.identify_challenges(str(current_employee.id), db)
        
        # Generate recommendations
        recommendations = await copilot.generate_recommendations(
            str(current_employee.id),
            trends,
            challenges,
            db
        )
        
        return {
            'success': True,
            'data': {
                'recommendations': recommendations,
                'count': len(recommendations),
            },
            'generated_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendations: {str(e)}"
        )


@router.get("/achievements")
async def get_achievements(
    days: int = 30,
    current_employee: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Get employee achievements and wins
    
    Celebrates accomplishments and positive trends.
    
    Args:
        days: Number of days to analyze (default: 30)
        current_employee: Authenticated employee
        db: Database session
    
    Returns:
        List of achievements
    """
    if days < 1 or days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 90"
        )
    
    try:
        copilot = EmployeeCopilot(db)
        achievements = await copilot.get_achievements(
            str(current_employee.id),
            days,
            db
        )
        
        return {
            'success': True,
            'data': {
                'achievements': achievements,
                'count': len(achievements),
                'period': f'Last {days} days',
            },
            'generated_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching achievements: {str(e)}"
        )


@router.get("/metrics")
async def get_metrics(
    current_employee: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Get key performance metrics for current employee
    
    Includes:
    - Trust score breakdown
    - Activity metrics (tasks, meetings)
    - Averages and trends
    
    Args:
        current_employee: Authenticated employee
        db: Database session
    
    Returns:
        Key performance metrics
    """
    try:
        copilot = EmployeeCopilot(db)
        metrics = await copilot.get_key_metrics(
            str(current_employee.id),
            db
        )
        
        return {
            'success': True,
            'data': metrics,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching metrics: {str(e)}"
        )


@router.get("/wellness")
async def get_wellness_insights(
    current_employee: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Get wellness insights for current employee
    
    Analyzes work patterns to provide wellness recommendations:
    - Work-life balance score
    - Burnout risk indicators
    - Wellness recommendations
    
    Args:
        current_employee: Authenticated employee
        db: Database session
    
    Returns:
        Wellness insights and recommendations
    """
    try:
        copilot = EmployeeCopilot(db)
        
        # Get trends
        trends = await copilot.get_trends(str(current_employee.id), 30, db)
        
        # Generate wellness insights
        wellness = copilot._generate_wellness_insights(trends)
        
        # Get wellness-specific recommendations
        challenges = await copilot.identify_challenges(str(current_employee.id), db)
        wellness_challenges = [
            c for c in challenges
            if c in ['late_night_work', 'weekend_work', 'long_work_days']
        ]
        
        recommendations = []
        if wellness_challenges:
            all_recommendations = await copilot.generate_recommendations(
                str(current_employee.id),
                trends,
                challenges,
                db
            )
            recommendations = [
                r for r in all_recommendations
                if r['category'] == 'wellness'
            ]
        
        return {
            'success': True,
            'data': {
                'wellness': wellness,
                'recommendations': recommendations,
                'challenges': wellness_challenges,
            },
            'generated_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating wellness insights: {str(e)}"
        )


@router.get("/productivity-patterns")
async def get_productivity_patterns(
    days: int = 30,
    current_employee: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Get productivity pattern analysis
    
    Analyzes when and how employee is most productive:
    - Peak productivity hours
    - Activity patterns
    - Consistency metrics
    
    Args:
        days: Number of days to analyze (default: 30)
        current_employee: Authenticated employee
        db: Database session
    
    Returns:
        Productivity pattern analysis
    """
    if days < 1 or days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 90"
        )
    
    try:
        copilot = EmployeeCopilot(db)
        trends = await copilot.get_trends(
            str(current_employee.id),
            days,
            db
        )
        
        return {
            'success': True,
            'data': {
                'patterns': trends.get('patterns', {}),
                'flags': trends.get('flags', []),
                'period': f'Last {days} days',
            },
            'generated_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing productivity patterns: {str(e)}"
        )


@router.get("/daily-summary")
async def get_daily_summary(
    current_employee: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily summary for current employee
    
    Quick snapshot of today's activity and key insights.
    
    Args:
        current_employee: Authenticated employee
        db: Database session
    
    Returns:
        Daily summary
    """
    try:
        copilot = EmployeeCopilot(db)
        
        # Get 1-day insights
        insights = await copilot.get_personalized_insights(
            str(current_employee.id),
            days=1
        )
        
        # Extract daily summary
        daily_summary = {
            'greeting': f"Hello, {current_employee.name}!",
            'summary': insights.get('summary', ''),
            'today_metrics': {
                'tasks': insights.get('metrics', {}).get('activity', {}).get('tasks_7d', 0),
                'meetings': insights.get('metrics', {}).get('activity', {}).get('meetings_7d', 0),
            },
            'top_recommendation': insights.get('recommendations', [{}])[0] if insights.get('recommendations') else None,
            'wellness_status': insights.get('wellness', {}).get('status', 'unknown'),
        }
        
        return {
            'success': True,
            'data': daily_summary,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating daily summary: {str(e)}"
        )
