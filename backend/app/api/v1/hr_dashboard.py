"""
HR Dashboard API
Cross-department behavioral and compliance monitoring.
HR sees all employees with behavioral focus — no raw network data, no system configs.

Requires: hr or admin role.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_hr_or_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr", tags=["hr-dashboard"])


# ── GET /hr/employees ──────────────────────────────────────────────────────────

@router.get("/employees")
async def get_all_employees(
    limit: int = Query(default=100, le=500),
    search: Optional[str] = Query(default=None),
    department: Optional[str] = Query(default=None),
    user: dict = Depends(require_hr_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    All employees across all departments.
    HR-visible fields only: no raw network traffic, no system config.
    """
    clauses = ["e.deleted_at IS NULL"]
    params: dict = {"limit": limit}

    if search:
        clauses.append("(e.name ILIKE :search OR e.email ILIKE :search)")
        params["search"] = f"%{search}%"
    if department:
        clauses.append("e.department ILIKE :dept")
        params["dept"] = f"%{department}%"

    where = "WHERE " + " AND ".join(clauses)

    result = await db.execute(
        text(f"""
            SELECT
                e.id::text  AS id,
                e.name,
                e.email,
                e.department,
                e.status,
                -- Latest trust score
                (
                    SELECT ts.total_score
                    FROM trust_scores ts
                    WHERE ts.employee_id = e.id
                    ORDER BY ts.timestamp DESC LIMIT 1
                ) AS trust_score,
                -- Active time estimation from behavioral data (seconds in last 24h)
                (
                    SELECT COUNT(*) * 30
                    FROM agent_events ae
                    JOIN agent_machines am ON ae.agent_id = am.id
                    WHERE LOWER(am.username) = LOWER(e.name)
                      AND ae.event_type = 'active_window'
                      AND ae.received_at >= NOW() - INTERVAL '24 hours'
                ) AS active_seconds_24h,
                e.created_at
            FROM employees e
            {where}
            ORDER BY e.department, e.name
            LIMIT :limit
        """),
        params,
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── GET /hr/behavioral ─────────────────────────────────────────────────────────

@router.get("/behavioral")
async def get_behavioral_data(
    limit: int = Query(default=50, le=200),
    department: Optional[str] = Query(default=None),
    user: dict = Depends(require_hr_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Behavioral pattern summary per employee.
    Shows activity ratios, idle patterns, event counts.
    Excludes: raw screenshots, network packets, system configs.
    """
    dept_clause = ""
    params: dict = {"limit": limit}
    if department:
        dept_clause = "AND e.department ILIKE :dept"
        params["dept"] = f"%{department}%"

    result = await db.execute(
        text(f"""
            SELECT
                e.id::text   AS employee_id,
                e.name       AS employee_name,
                e.department,
                COUNT(ae.id) FILTER (WHERE ae.event_type = 'active_window') AS active_events,
                COUNT(ae.id) FILTER (WHERE ae.event_type = 'idle')          AS idle_events,
                COUNT(ae.id) FILTER (WHERE ae.event_type = 'usb_devices')   AS usb_events,
                COUNT(ae.id) FILTER (WHERE ae.event_type = 'file_activity') AS file_events,
                COUNT(ae.id) FILTER (WHERE ae.event_type = 'websites')      AS website_events,
                COUNT(ae.id)                                                  AS total_events,
                MAX(ae.received_at)                                           AS last_seen
            FROM employees e
            LEFT JOIN agent_machines am ON LOWER(am.username) = LOWER(e.name)
            LEFT JOIN agent_events ae   ON ae.agent_id = am.id
                AND ae.received_at >= NOW() - INTERVAL '7 days'
            WHERE e.deleted_at IS NULL
            {dept_clause}
            GROUP BY e.id, e.name, e.department
            ORDER BY total_events DESC
            LIMIT :limit
        """),
        params,
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── GET /hr/anomalies ──────────────────────────────────────────────────────────

@router.get("/anomalies")
async def get_all_anomalies(
    limit: int = Query(default=50, le=200),
    severity: Optional[str] = Query(default=None, description="critical | warning | info"),
    user: dict = Depends(require_hr_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Cross-department anomaly report.
    Employees whose trust score is below threshold, aggregated for HR review.
    No system-level config data exposed.
    """
    severity_filter = ""
    params: dict = {"limit": limit}

    if severity == "critical":
        severity_filter = "AND ts.total_score < 40"
    elif severity == "warning":
        severity_filter = "AND ts.total_score BETWEEN 40 AND 59"
    else:
        severity_filter = "AND ts.total_score < 70"

    result = await db.execute(
        text(f"""
            SELECT
                e.id::text  AS employee_id,
                e.name      AS employee_name,
                e.email,
                e.department,
                ts.total_score,
                ts.behavioral_score,
                ts.security_score,
                ts.wellbeing_score,
                ts.timestamp AS score_time,
                CASE
                    WHEN ts.total_score < 40 THEN 'critical'
                    WHEN ts.total_score < 60 THEN 'warning'
                    ELSE 'info'
                END AS severity
            FROM employees e
            JOIN trust_scores ts ON ts.employee_id = e.id
            WHERE
                e.deleted_at IS NULL
                {severity_filter}
                AND ts.timestamp = (
                    SELECT MAX(ts2.timestamp)
                    FROM trust_scores ts2 WHERE ts2.employee_id = e.id
                )
            ORDER BY ts.total_score ASC, e.department
            LIMIT :limit
        """),
        params,
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── GET /hr/trust-trends ───────────────────────────────────────────────────────

@router.get("/trust-trends")
async def get_trust_trends(
    days: int = Query(default=30, le=90, description="Look-back window in days"),
    department: Optional[str] = Query(default=None),
    user: dict = Depends(require_hr_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Department-level trust score trends over time.
    Aggregated daily averages — no individual raw configs.
    """
    dept_clause = ""
    params: dict = {"days": days}
    if department:
        dept_clause = "AND e.department ILIKE :dept"
        params["dept"] = f"%{department}%"

    result = await db.execute(
        text(f"""
            SELECT
                DATE_TRUNC('day', ts.timestamp) AS date,
                e.department,
                ROUND(AVG(ts.total_score)::numeric, 1)      AS avg_score,
                ROUND(AVG(ts.behavioral_score)::numeric, 1)  AS avg_behavioral,
                COUNT(DISTINCT e.id)                          AS employee_count
            FROM trust_scores ts
            JOIN employees e ON e.id = ts.employee_id
            WHERE ts.timestamp >= NOW() - INTERVAL ':days days'
              AND e.deleted_at IS NULL
              {dept_clause}
            GROUP BY DATE_TRUNC('day', ts.timestamp), e.department
            ORDER BY date, e.department
        """),
        params,
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── GET /hr/compliance-logs ────────────────────────────────────────────────────

@router.get("/compliance-logs")
async def get_compliance_logs(
    limit: int = Query(default=50, le=200),
    employee_id: Optional[str] = Query(default=None),
    user: dict = Depends(require_hr_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Agent send audit trail for compliance review.
    HR can view who received agent emails and when.
    """
    where = ""
    params: dict = {"limit": limit}
    if employee_id:
        where = "WHERE employee_id = :employee_id"
        params["employee_id"] = employee_id

    result = await db.execute(
        text(f"""
            SELECT
                id::text         AS id,
                admin_id,
                employee_id,
                employee_email,
                employee_name,
                status,
                sent_at
            FROM agent_send_logs
            {where}
            ORDER BY sent_at DESC
            LIMIT :limit
        """),
        params,
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── GET /hr/stats ──────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_hr_stats(
    user: dict = Depends(require_hr_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """Organisation-wide summary stats for the HR dashboard header."""
    result = await db.execute(
        text("""
            SELECT
                COUNT(DISTINCT e.id)                                          AS total_employees,
                COUNT(DISTINCT e.department)                                  AS total_departments,
                ROUND(AVG(ts.total_score)::numeric, 1)                        AS org_avg_trust_score,
                COUNT(DISTINCT e.id) FILTER (WHERE ts.total_score < 60)       AS at_risk_count,
                COUNT(DISTINCT e.id) FILTER (WHERE ts.total_score >= 75)      AS good_standing_count,
                COUNT(DISTINCT e.id) FILTER (WHERE e.status = 'active')       AS active_employees
            FROM employees e
            LEFT JOIN trust_scores ts ON ts.employee_id = e.id
                AND ts.timestamp = (
                    SELECT MAX(ts2.timestamp) FROM trust_scores ts2 WHERE ts2.employee_id = e.id
                )
            WHERE e.deleted_at IS NULL
        """)
    )
    row = result.fetchone()
    return dict(row._mapping) if row else {}
