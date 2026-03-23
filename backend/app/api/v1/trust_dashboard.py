"""
Admin Trust Scores Dashboard API
Provides aggregated trust score data for the admin Trust Dashboard.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["trust-dashboard"])


@router.get("/trust-scores")
async def get_trust_scores(db: AsyncSession = Depends(get_db)):
    """
    Returns the latest trust score for every active employee.
    No auth required for now — add auth dependency if needed.
    Called by the Admin TrustDashboard component.
    """
    result = await db.execute(text("""
        SELECT
            e.id::text          AS employee_id,
            e.name,
            e.email,
            e.department,
            e.status,
            COALESCE(ts.total_score,      0) AS total_score,
            COALESCE(ts.outcome_score,    0) AS outcome_score,
            COALESCE(ts.behavioral_score, 0) AS behavioral_score,
            COALESCE(ts.security_score,   0) AS security_score,
            COALESCE(ts.wellbeing_score,  0) AS wellbeing_score,
            ts.timestamp AS score_time
        FROM employees e
        LEFT JOIN LATERAL (
            SELECT total_score, outcome_score, behavioral_score, security_score,
                   wellbeing_score, timestamp
            FROM trust_scores
            WHERE employee_id = e.id
            ORDER BY timestamp DESC
            LIMIT 1
        ) ts ON TRUE
        WHERE e.deleted_at IS NULL
          AND e.status = 'active'
        ORDER BY total_score ASC NULLS LAST
    """))
    rows = result.fetchall()

    # Return an empty list if no employees yet — the dashboard handles this gracefully
    return [dict(r._mapping) for r in rows]
