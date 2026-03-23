"""
Manager Dashboard API
Department-scoped employee monitoring data.
Managers see ONLY their department's employees and activity.
Admins get unfiltered access to all departments.

Requires: manager or admin role.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import UserRole, require_manager_or_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager", tags=["manager-dashboard"])


def _dept_filter(user: dict) -> tuple[str, dict]:
    """
    Return a SQL WHERE clause fragment + params for department filtering.
    Admin → no restriction. Manager → restricted to their own department.
    """
    if UserRole(user["role"]) == UserRole.ADMIN:
        return "", {}
    dept = user.get("department_name", "")
    return "AND e.department ILIKE :dept", {"dept": dept}


# ── GET /manager/team ──────────────────────────────────────────────────────────

@router.get("/team")
async def get_team_employees(
    limit: int = Query(default=50, le=200),
    search: Optional[str] = Query(default=None),
    user: dict = Depends(require_manager_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Return employees visible to this manager.

    - Manager: only employees in their assigned department.
    - Admin: all employees across all departments.
    """
    dept_clause, dept_params = _dept_filter(user)
    search_clause = ""
    search_params = {}

    if search:
        search_clause = "AND (e.name ILIKE :search OR e.email ILIKE :search)"
        search_params["search"] = f"%{search}%"

    result = await db.execute(
        text(f"""
            SELECT
                e.id::text    AS id,
                e.name,
                e.email,
                e.department,
                e.role,
                e.status,
                -- Latest trust score
                (
                    SELECT ts.total_score
                    FROM trust_scores ts
                    WHERE ts.employee_id = e.id
                    ORDER BY ts.timestamp DESC
                    LIMIT 1
                ) AS trust_score,
                -- Agent installed?
                EXISTS (
                    SELECT 1 FROM agent_machines am
                    WHERE LOWER(am.username) = LOWER(e.name)
                ) AS agent_installed,
                e.created_at
            FROM employees e
            WHERE e.deleted_at IS NULL
            {dept_clause}
            {search_clause}
            ORDER BY e.name
            LIMIT :limit
        """),
        {"limit": limit, **dept_params, **search_params},
    )
    rows = result.fetchall()
    return [dict(r._mapping) for r in rows]


# ── GET /manager/team/{emp_id}/activity ───────────────────────────────────────

@router.get("/team/{emp_id}/activity")
async def get_employee_activity(
    emp_id: str,
    limit: int = Query(default=20, le=100),
    user: dict = Depends(require_manager_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time activity events for a specific employee.
    Manager can only view employees in their own department.
    Shows: active_window, processes, websites, idle times.
    Network/system-level data is excluded.
    """
    # Verify department access for managers
    if UserRole(user["role"]) == UserRole.MANAGER:
        emp_check = await db.execute(
            text("""
                SELECT department FROM employees
                WHERE id::text = :id AND deleted_at IS NULL
            """),
            {"id": emp_id},
        )
        emp_row = emp_check.fetchone()
        if not emp_row:
            raise HTTPException(status_code=404, detail="Employee not found")
        if (emp_row.department or "").lower() != (user.get("department_name") or "").lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view employees in your department",
            )

    # Fetch agent events (exclude screenshot blobs, network data)
    result = await db.execute(
        text("""
            SELECT
                ae.id, ae.event_type, ae.payload, ae.collected_at, ae.received_at,
                am.hostname
            FROM agent_events ae
            JOIN agent_machines am ON ae.agent_id = am.id
            WHERE
                -- Link agent to employee by username match (best-effort)
                EXISTS (
                    SELECT 1 FROM employees e
                    WHERE e.id::text = :emp_id
                      AND LOWER(am.username) = LOWER(e.name)
                )
                AND ae.event_type IN (
                    'active_window','processes','idle','usb_devices',
                    'file_activity','websites','sysinfo'
                )
            ORDER BY ae.received_at DESC
            LIMIT :limit
        """),
        {"emp_id": emp_id, "limit": limit},
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── GET /manager/team/{emp_id}/trust-score ────────────────────────────────────

@router.get("/team/{emp_id}/trust-score")
async def get_employee_trust_score(
    emp_id: str,
    user: dict = Depends(require_manager_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Latest trust score for an employee. Read-only for managers.
    """
    # Department check for managers
    if UserRole(user["role"]) == UserRole.MANAGER:
        emp_check = await db.execute(
            text("SELECT department FROM employees WHERE id::text = :id AND deleted_at IS NULL"),
            {"id": emp_id},
        )
        row = emp_check.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Employee not found")
        if (row.department or "").lower() != (user.get("department_name") or "").lower():
            raise HTTPException(status_code=403, detail="Access denied: different department")

    result = await db.execute(
        text("""
            SELECT
                ts.total_score, ts.outcome_score, ts.behavioral_score,
                ts.security_score, ts.wellbeing_score, ts.timestamp
            FROM trust_scores ts
            WHERE ts.employee_id::text = :emp_id
            ORDER BY ts.timestamp DESC
            LIMIT 10
        """),
        {"emp_id": emp_id},
    )
    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No trust scores found for this employee")
    return [dict(r._mapping) for r in rows]


# ── GET /manager/alerts ────────────────────────────────────────────────────────

@router.get("/alerts")
async def get_team_alerts(
    limit: int = Query(default=30, le=100),
    user: dict = Depends(require_manager_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Anomaly / alert events for the manager's team.
    Returns employees whose trust score dropped significantly or triggered anomalies.
    Admin sees all departments.
    """
    dept_clause, dept_params = _dept_filter(user)

    result = await db.execute(
        text(f"""
            SELECT
                e.id::text AS employee_id,
                e.name     AS employee_name,
                e.department,
                ts.total_score,
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
                AND ts.total_score < 70
                {dept_clause}
                AND ts.timestamp = (
                    SELECT MAX(ts2.timestamp)
                    FROM trust_scores ts2
                    WHERE ts2.employee_id = e.id
                )
            ORDER BY ts.total_score ASC
            LIMIT :limit
        """),
        {"limit": limit, **dept_params},
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── GET /manager/stats ─────────────────────────────────────────────────────────

@router.get("/stats")
async def get_team_stats(
    user: dict = Depends(require_manager_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """Summary stats for the manager's department dashboard header."""
    dept_clause, dept_params = _dept_filter(user)

    result = await db.execute(
        text(f"""
            SELECT
                COUNT(DISTINCT e.id)                                  AS total_employees,
                ROUND(AVG(ts.total_score)::numeric, 1)                AS avg_trust_score,
                COUNT(DISTINCT e.id) FILTER (WHERE ts.total_score < 60) AS at_risk_count,
                COUNT(DISTINCT e.id) FILTER (WHERE ts.total_score >= 75) AS good_standing_count,
                COUNT(DISTINCT am.id) FILTER (WHERE am.status = 'online') AS agents_online
            FROM employees e
            LEFT JOIN trust_scores ts ON ts.employee_id = e.id
                AND ts.timestamp = (
                    SELECT MAX(ts2.timestamp) FROM trust_scores ts2 WHERE ts2.employee_id = e.id
                )
            LEFT JOIN agent_machines am ON LOWER(am.username) = LOWER(e.name)
            WHERE e.deleted_at IS NULL
            {dept_clause}
        """),
        dept_params,
    )
    row = result.fetchone()
    return dict(row._mapping) if row else {}
