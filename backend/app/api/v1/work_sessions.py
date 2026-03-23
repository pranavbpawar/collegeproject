"""
TBAPS — Work Sessions API
Clock-in / clock-out tracking for employees via the NEF client app.

Endpoints:
  POST /api/v1/work/clock-in         — employee clocks in
  POST /api/v1/work/clock-out        — employee clocks out
  GET  /api/v1/work/my-sessions      — employee views own sessions
  GET  /api/v1/work/sessions         — manager/HR views employee sessions
  GET  /api/v1/work/sessions/summary — aggregated hours summary
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_rbac_user, UserRole, require_manager_or_admin
from app.api.v1.employee_auth import get_current_employee

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/work", tags=["work-sessions"])


# ── Request / Response models ──────────────────────────────────────────────────

class ClockInRequest(BaseModel):
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    notes: Optional[str] = None


# ── Employee Endpoints ─────────────────────────────────────────────────────────

@router.post("/clock-in", status_code=201)
async def clock_in(
    body:     ClockInRequest,
    employee: dict = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    Clock the employee in.
    Fails if there is already an open (not clocked-out) session for today.
    """
    # Check for already-open session
    existing = await db.execute(
        text("""
            SELECT id::text AS id, clock_in::text AS clock_in
            FROM work_sessions
            WHERE employee_id::text = :emp_id AND clock_out IS NULL
            ORDER BY clock_in DESC LIMIT 1
        """),
        {"emp_id": employee["id"]},
    )
    open_session = existing.fetchone()
    if open_session:
        raise HTTPException(
            status_code=409,
            detail=f"You already have an open session since {open_session.clock_in}. Clock out first.",
        )

    session_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO work_sessions
                (id, employee_id, clock_in, notes, created_at)
            VALUES (:id::uuid, :emp_id::uuid, NOW(), :notes, NOW())
        """),
        {"id": session_id, "emp_id": employee["id"], "notes": body.notes},
    )
    await db.commit()

    return {
        "ok":         True,
        "session_id": session_id,
        "message":    "Clocked in successfully.",
        "clock_in":   datetime.now(timezone.utc).isoformat(),
    }


@router.post("/clock-out", status_code=200)
async def clock_out(
    body:     ClockOutRequest,
    employee: dict = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    Clock the employee out. Calculates and stores duration in minutes.
    """
    existing = await db.execute(
        text("""
            SELECT id::text AS id, clock_in
            FROM work_sessions
            WHERE employee_id::text = :emp_id AND clock_out IS NULL
            ORDER BY clock_in DESC LIMIT 1
        """),
        {"emp_id": employee["id"]},
    )
    row = existing.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="No open session found. You are not clocked in.",
        )

    now = datetime.now(timezone.utc)
    duration_minutes = int((now - row.clock_in.replace(tzinfo=timezone.utc)).total_seconds() / 60)

    await db.execute(
        text("""
            UPDATE work_sessions
            SET clock_out         = NOW(),
                duration_minutes  = :dur,
                notes             = COALESCE(:notes, notes)
            WHERE id::text = :session_id
        """),
        {"dur": duration_minutes, "notes": body.notes, "session_id": row.id},
    )
    await db.commit()

    hours   = duration_minutes // 60
    minutes = duration_minutes  % 60

    return {
        "ok":               True,
        "session_id":       row.id,
        "message":          f"Clocked out. Duration: {hours}h {minutes}m.",
        "clock_out":        now.isoformat(),
        "duration_minutes": duration_minutes,
        "duration_human":   f"{hours}h {minutes}m",
    }


@router.get("/my-sessions")
async def my_sessions(
    limit:    int = Query(default=30, le=200),
    employee: dict = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated employee's own work sessions (newest first)."""
    result = await db.execute(
        text("""
            SELECT
                id::text AS id,
                clock_in::text AS clock_in,
                clock_out::text AS clock_out,
                duration_minutes,
                notes,
                created_at::text AS created_at
            FROM work_sessions
            WHERE employee_id::text = :emp_id
            ORDER BY clock_in DESC
            LIMIT :limit
        """),
        {"emp_id": employee["id"], "limit": limit},
    )
    rows = result.fetchall()
    sessions = []
    for r in rows:
        s = dict(r._mapping)
        if s["duration_minutes"] is not None:
            h = s["duration_minutes"] // 60
            m = s["duration_minutes"] % 60
            s["duration_human"] = f"{h}h {m}m"
        else:
            s["duration_human"] = "In progress"
        sessions.append(s)
    return sessions


@router.get("/my-summary")
async def my_summary(
    employee: dict = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """Return total hours worked this week and today for the employee."""
    result = await db.execute(
        text("""
            SELECT
                COALESCE(SUM(duration_minutes) FILTER (
                    WHERE clock_in >= date_trunc('week', NOW())
                ), 0) AS week_minutes,
                COALESCE(SUM(duration_minutes) FILTER (
                    WHERE clock_in >= date_trunc('day', NOW())
                ), 0) AS today_minutes,
                COUNT(*) FILTER (WHERE clock_out IS NULL) AS open_sessions
            FROM work_sessions
            WHERE employee_id::text = :emp_id
        """),
        {"emp_id": employee["id"]},
    )
    row = result.fetchone()
    d = dict(row._mapping)
    wm = int(d["week_minutes"] or 0)
    tm = int(d["today_minutes"] or 0)
    return {
        "today_minutes":   tm,
        "today_human":     f"{tm // 60}h {tm % 60}m",
        "week_minutes":    wm,
        "week_human":      f"{wm // 60}h {wm % 60}m",
        "open_sessions":   int(d["open_sessions"] or 0),
    }


# ── Manager / HR Endpoints ─────────────────────────────────────────────────────

@router.get("/sessions")
async def get_employee_sessions(
    employee_id: str = Query(...),
    limit:       int = Query(default=50, le=500),
    user: dict = Depends(require_manager_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    View work sessions for a specific employee.
    Manager: restricted to their department.
    Admin: unrestricted.
    """
    # Department access check for managers
    if UserRole(user["role"]) == UserRole.MANAGER:
        emp_check = await db.execute(
            text("SELECT department FROM employees WHERE id::text = :id AND deleted_at IS NULL"),
            {"id": employee_id},
        )
        emp_row = emp_check.fetchone()
        if not emp_row:
            raise HTTPException(status_code=404, detail="Employee not found.")
        if (emp_row.department or "").lower() != (user.get("department_name") or "").lower():
            raise HTTPException(status_code=403, detail="Access denied: different department.")

    result = await db.execute(
        text("""
            SELECT
                ws.id::text AS id,
                ws.employee_id::text AS employee_id,
                e.name AS employee_name,
                ws.clock_in::text AS clock_in,
                ws.clock_out::text AS clock_out,
                ws.duration_minutes,
                ws.notes,
                ws.created_at::text AS created_at
            FROM work_sessions ws
            JOIN employees e ON e.id = ws.employee_id
            WHERE ws.employee_id::text = :emp_id
            ORDER BY ws.clock_in DESC
            LIMIT :limit
        """),
        {"emp_id": employee_id, "limit": limit},
    )
    rows = result.fetchall()
    sessions = []
    for r in rows:
        s = dict(r._mapping)
        dm = s.get("duration_minutes")
        s["duration_human"] = f"{dm // 60}h {dm % 60}m" if dm is not None else "In progress"
        sessions.append(s)
    return sessions


@router.get("/sessions/summary")
async def get_hours_summary(
    user: dict = Depends(require_manager_or_admin()),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregated hours-worked summary for the manager's department.
    Shows total hours per employee this week.
    """
    dept_clause = ""
    params: dict = {}
    if UserRole(user["role"]) == UserRole.MANAGER:
        dept_clause = "AND e.department ILIKE :dept"
        params["dept"] = user.get("department_name", "")

    result = await db.execute(
        text(f"""
            SELECT
                e.id::text AS employee_id,
                e.name AS employee_name,
                e.department,
                COALESCE(SUM(ws.duration_minutes) FILTER (
                    WHERE ws.clock_in >= date_trunc('week', NOW())
                ), 0) AS week_minutes,
                COALESCE(SUM(ws.duration_minutes) FILTER (
                    WHERE ws.clock_in >= date_trunc('day', NOW())
                ), 0) AS today_minutes,
                COUNT(ws.id) FILTER (WHERE ws.clock_out IS NULL) AS open_sessions
            FROM employees e
            LEFT JOIN work_sessions ws ON ws.employee_id = e.id
            WHERE e.deleted_at IS NULL
              {dept_clause}
            GROUP BY e.id, e.name, e.department
            ORDER BY week_minutes DESC
        """),
        params,
    )
    rows = result.fetchall()
    summaries = []
    for r in rows:
        s = dict(r._mapping)
        wm = int(s["week_minutes"] or 0)
        tm = int(s["today_minutes"] or 0)
        s["week_hours_human"]  = f"{wm // 60}h {wm % 60}m"
        s["today_hours_human"] = f"{tm // 60}h {tm % 60}m"
        summaries.append(s)
    return summaries
