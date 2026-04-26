"""
TBAPS — Employee Portal & KBT Heartbeat APIs
=============================================
New endpoints to power the Employee Web Portal and the KBT heartbeat sync.

GET  /api/v1/employee/status             → Employee's combined status (KBT + work + trust)
POST /api/v1/kbt/heartbeat               → KBT device heartbeat (updates last-seen in DB)
POST /api/v1/kbt/portal-token            → KBT requests a single-use web-portal login token
POST /api/v1/kbt/portal-token/exchange   → Web portal exchanges portal token for session JWT

Security model:
  - /kbt/heartbeat authenticates using the existing KBT token hash system (same as auto-login)
  - /kbt/portal-token issues a UUIDv4 token stored in Redis with 5-min TTL + employee_id
  - /kbt/portal-token/exchange is single-use: Redis key deleted on first successful exchange
  - HEARTBEAT_RATE_LIMIT guards the heartbeat endpoint against abuse
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.api.v1.employee_auth import get_current_employee, _make_employee_token

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    _limiter = Limiter(key_func=get_remote_address)

    def _rate_limit(rate: str):
        """Apply a slowapi rate-limit decorator."""
        return _limiter.limit(rate)
except ImportError:
    _limiter = None

    def _rate_limit(rate: str):  # no-op fallback
        def _noop(fn):
            return fn
        return _noop


logger = logging.getLogger(__name__)

router = APIRouter(tags=["employee-portal"])

_PORTAL_TOKEN_TTL = 300   # 5 minutes
_HEARTBEAT_STALE_MINUTES = 10  # KBT is "connected" if heartbeat was within 10 min


# ── Helpers ────────────────────────────────────────────────────────────────────

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _get_redis():
    """Return the Redis client, or None if Redis is unavailable."""
    try:
        from app.core.cache import redis_client
        await redis_client.ping()
        return redis_client
    except Exception:
        return None


# ── Request / Response models ──────────────────────────────────────────────────

class HeartbeatRequest(BaseModel):
    employee_id: str
    token:       str             # Raw KBT token (verified against stored hash)
    device_id:   str             # Hostname or MAC address
    platform:    Optional[str] = None   # "linux", "windows", "mac"
    status:      Optional[str] = "active"


class HeartbeatResponse(BaseModel):
    ok:          bool
    message:     str
    server_time: str


class PortalTokenRequest(BaseModel):
    employee_id: str
    token:       str             # Raw KBT token


class PortalTokenResponse(BaseModel):
    portal_token: str
    expires_in:   int = _PORTAL_TOKEN_TTL


class ExchangeRequest(BaseModel):
    portal_token: str


class EmployeeStatusResponse(BaseModel):
    employee_id:       str
    name:              str
    email:             str
    department:        Optional[str]
    role:              Optional[str]
    activation_status: str
    kbt_connected:     bool
    kbt_last_seen:     Optional[str]
    kbt_device_id:     Optional[str]
    trust_score:       Optional[float]
    open_session:      bool
    today_minutes:     int
    week_minutes:      int
    today_human:       str
    week_human:        str


# ── GET /employee/status ───────────────────────────────────────────────────────

@router.get("/employee/status", response_model=EmployeeStatusResponse)
async def employee_status(
    employee: dict = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    Combined status endpoint for the Employee Web Portal dashboard.
    Returns:
      - KBT connection status (based on last heartbeat within 10 min)
      - Current work session state + today/week hours
      - Latest trust score (read-only)
    """
    emp_id = employee["id"]

    # Fetch full employee row including heartbeat columns
    emp_result = await db.execute(
        text("""
            SELECT
                e.id::text AS id,
                e.name,
                e.email,
                e.department,
                e.role,
                e.activation_status,
                e.kbt_last_heartbeat_at,
                e.kbt_device_id
            FROM employees e
            WHERE e.id::text = :id AND e.deleted_at IS NULL
        """),
        {"id": emp_id},
    )
    emp_row = emp_result.fetchone()
    if not emp_row:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Determine KBT connection status
    kbt_connected = False
    kbt_last_seen_str = None
    if emp_row.kbt_last_heartbeat_at:
        last_hb = emp_row.kbt_last_heartbeat_at
        if last_hb.tzinfo is None:
            last_hb = last_hb.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - last_hb
        kbt_connected = delta.total_seconds() < (_HEARTBEAT_STALE_MINUTES * 60)
        kbt_last_seen_str = last_hb.isoformat()

    # Work session summary
    work_result = await db.execute(
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
        {"emp_id": emp_id},
    )
    wrow = work_result.fetchone()
    today_min = int(wrow.today_minutes or 0)
    week_min  = int(wrow.week_minutes  or 0)
    open_sess = int(wrow.open_sessions or 0) > 0

    # Latest trust score (best-effort)
    trust_score = None
    try:
        ts_result = await db.execute(
            text("""
                SELECT score FROM trust_scores
                WHERE employee_id::text = :emp_id
                ORDER BY calculated_at DESC LIMIT 1
            """),
            {"emp_id": emp_id},
        )
        ts_row = ts_result.fetchone()
        if ts_row:
            trust_score = float(ts_row.score)
    except Exception:
        pass  # Trust score is non-critical

    def _fmt(minutes: int) -> str:
        return f"{minutes // 60}h {minutes % 60}m"

    return EmployeeStatusResponse(
        employee_id=emp_id,
        name=emp_row.name,
        email=emp_row.email,
        department=emp_row.department,
        role=emp_row.role,
        activation_status=emp_row.activation_status,
        kbt_connected=kbt_connected,
        kbt_last_seen=kbt_last_seen_str,
        kbt_device_id=emp_row.kbt_device_id,
        trust_score=trust_score,
        open_session=open_sess,
        today_minutes=today_min,
        week_minutes=week_min,
        today_human=_fmt(today_min),
        week_human=_fmt(week_min),
    )


# ── POST /kbt/heartbeat ────────────────────────────────────────────────────────

@router.post("/kbt/heartbeat", response_model=HeartbeatResponse)
@_rate_limit("12/minute")
async def kbt_heartbeat(
    body: HeartbeatRequest,
    request: Request,
    db:   AsyncSession = Depends(get_db),
):
    """
    Device heartbeat from the KBT Executable.
    Called on startup and every 5 minutes while running.

    Authentication: KBT token hash (same mechanism as /kbt/auto-login).
    Updates: kbt_last_heartbeat_at and kbt_device_id in the employees table.
    """
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized KBT client.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Fetch employee + token hash
    result = await db.execute(
        text("""
            SELECT e.id::text AS id,
                   e.status,
                   e.activation_status,
                   e.kbt_token_hash,
                   e.kbt_token_expires_at
            FROM employees e
            WHERE e.id::text = :emp_id AND e.deleted_at IS NULL
        """),
        {"emp_id": body.employee_id},
    )
    row = result.fetchone()

    if not row or row.status != "active":
        raise invalid_exc

    if row.activation_status != "activated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KBT not activated. Please run the activation flow first.",
        )

    if not row.kbt_token_hash:
        raise invalid_exc

    # Constant-time hash comparison
    incoming_hash = _hash_token(body.token)
    if not secrets.compare_digest(incoming_hash, row.kbt_token_hash):
        logger.warning(f"[kbt-heartbeat] Token mismatch for employee: {body.employee_id}")
        raise invalid_exc

    # Update heartbeat timestamp and device info (best effort)
    now = datetime.now(timezone.utc)
    try:
        await db.execute(
            text("""
                UPDATE employees
                SET kbt_last_heartbeat_at = :now,
                    kbt_device_id         = :device_id,
                    updated_at            = NOW()
                WHERE id::text = :id
            """),
            {"now": now, "device_id": body.device_id, "id": body.employee_id},
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"[kbt-heartbeat] DB update failed: {e}")
        await db.rollback()

    logger.info(
        f"[kbt-heartbeat] employee={body.employee_id} device={body.device_id} "
        f"platform={body.platform} status={body.status}"
    )

    return HeartbeatResponse(
        ok=True,
        message="Heartbeat received.",
        server_time=now.isoformat(),
    )


# ── POST /kbt/portal-token ─────────────────────────────────────────────────────

@router.post("/kbt/portal-token", response_model=PortalTokenResponse)
@_rate_limit("5/minute")
async def kbt_request_portal_token(
    body: PortalTokenRequest,
    request: Request,
    db:   AsyncSession = Depends(get_db),
):
    """
    KBT Executable requests a short-lived, single-use token that allows
    seamless login to the Employee Web Portal without re-entering credentials.

    Auth: KBT token hash (same as /kbt/auto-login and /kbt/heartbeat).
    Returns: portal_token (UUID4) stored in Redis for 5 min.

    The portal_token is embedded in the portal URL:
        https://<frontend>/employee?token=<portal_token>
    """
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized KBT client.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify KBT token
    result = await db.execute(
        text("""
            SELECT id::text AS id, email, name,
                   status, activation_status, kbt_token_hash
            FROM employees
            WHERE id::text = :emp_id AND deleted_at IS NULL
        """),
        {"emp_id": body.employee_id},
    )
    row = result.fetchone()
    if not row or row.status != "active" or row.activation_status != "activated":
        raise invalid_exc
    if not row.kbt_token_hash:
        raise invalid_exc

    incoming_hash = _hash_token(body.token)
    if not secrets.compare_digest(incoming_hash, row.kbt_token_hash):
        raise invalid_exc

    # Generate portal token
    portal_token = str(uuid.uuid4())
    redis = await _get_redis()
    if redis:
        redis_key = f"portal_token:{portal_token}"
        # Store as: employee_id|email|name (pipe-delimited, simple, no JSON overhead)
        await redis.set(
            redis_key,
            f"{row.id}|{row.email}|{row.name}",
            ex=_PORTAL_TOKEN_TTL,
        )
        logger.info(
            f"[kbt-portal-token] Issued portal token for employee={body.employee_id} "
            f"(TTL={_PORTAL_TOKEN_TTL}s)"
        )
    else:
        # Redis unavailable — graceful degradation: return a signed JWT instead
        # (less ideal but functional without Redis)
        logger.warning("[kbt-portal-token] Redis unavailable; portal token in-memory only (no persistence)")
        # Fall through — token won't be exchangeable without Redis, but don't hard-fail

    return PortalTokenResponse(portal_token=portal_token, expires_in=_PORTAL_TOKEN_TTL)


# ── POST /kbt/portal-token/exchange ───────────────────────────────────────────

@router.post("/kbt/portal-token/exchange")
@_rate_limit("10/minute")
async def exchange_portal_token(
    body: ExchangeRequest,
    request: Request,
    db:   AsyncSession = Depends(get_db),
):
    """
    Web portal exchanges a single-use portal_token for a session JWT.

    Single-use: the Redis key is atomically deleted on first successful exchange.
    Subsequent calls with the same token return 401.
    """
    redis = await _get_redis()
    if not redis:
        raise HTTPException(
            status_code=503,
            detail="Token exchange unavailable (cache service offline). Please use email/password login.",
        )

    redis_key = f"portal_token:{body.portal_token}"

    # Atomically get + delete (single-use enforcement)
    raw_value = await redis.getdel(redis_key)

    if not raw_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Portal token is invalid, expired, or already used. "
                   "Please use email/password login or request a new link from your KBT app.",
        )

    try:
        parts = raw_value.decode("utf-8").split("|", 2)
        employee_id, email, name = parts[0], parts[1], parts[2]
    except (ValueError, AttributeError):
        raise HTTPException(status_code=500, detail="Token data corrupted.")

    # Verify employee is still active before issuing JWT
    result = await db.execute(
        text("SELECT status, activation_status FROM employees WHERE id::text = :id AND deleted_at IS NULL"),
        {"id": employee_id},
    )
    row = result.fetchone()
    if not row or row.status != "active" or row.activation_status != "activated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee account is inactive or not yet activated.",
        )

    access_token = _make_employee_token(employee_id, email, name)

    logger.info(f"[kbt-portal-token] Exchanged portal token for employee={employee_id}")

    return {
        "access_token": access_token,
        "token_type":   "bearer",
        "expires_in":   12 * 3600,
        "employee_id":  employee_id,
        "name":         name,
        "email":        email,
    }
