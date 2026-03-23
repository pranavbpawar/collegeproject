"""
TBAPS — Employee Auth Endpoints
POST /api/v1/employee/login    → Employee logs into the NEF client app
GET  /api/v1/employee/me       → Returns employee profile
POST /api/v1/employee/set-password  → Set/reset employee app password (admin/HR)

Employees authenticate using their email + a dedicated app password.
A separate employee JWT is issued (type='employee') to keep it isolated from
the admin/manager/HR RBAC token flow.
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/employee", tags=["employee-auth"])

# Separate OAuth scheme for employee tokens (different tokenUrl)
employee_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/employee/login", auto_error=False)

_EMPLOYEE_TOKEN_TTL_HOURS = 12


# ── Helpers ────────────────────────────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _make_employee_token(employee_id: str, email: str, name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_EMPLOYEE_TOKEN_TTL_HOURS)
    payload = {
        "sub":   employee_id,
        "email": email,
        "name":  name,
        "type":  "employee",
        "exp":   expire,
        "jti":   secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── Auth Dependency ────────────────────────────────────────────────────────────

async def get_current_employee(
    token: str = Depends(employee_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    FastAPI dependency — decode employee JWT and verify employee is still active.
    Used by all chat / work-session endpoints accessed by employees.
    """
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired employee token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise creds_exc
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        if payload.get("type") != "employee":
            raise creds_exc
        employee_id: str = payload.get("sub")
        if not employee_id:
            raise creds_exc
    except JWTError:
        raise creds_exc

    # Verify employee is still active
    result = await db.execute(
        text("""
            SELECT e.id::text AS id, e.email, e.name, e.department, e.role, e.status,
                   ea.is_active AS auth_active
            FROM employees e
            JOIN employee_auth ea ON ea.employee_id = e.id
            WHERE e.id::text = :id AND e.deleted_at IS NULL
        """),
        {"id": employee_id},
    )
    row = result.fetchone()
    if not row or not row.auth_active or row.status != "active":
        raise creds_exc

    return dict(row._mapping)


# ── Response Models ────────────────────────────────────────────────────────────

class EmployeeLoginResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int = _EMPLOYEE_TOKEN_TTL_HOURS * 3600
    employee_id:  str
    name:         str
    email:        str
    department:   Optional[str]
    role:         Optional[str]


class EmployeeMeResponse(BaseModel):
    id:         str
    email:      str
    name:       str
    department: Optional[str]
    role:       Optional[str]
    status:     str


class SetPasswordRequest(BaseModel):
    employee_email: str
    new_password:   str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/login", response_model=EmployeeLoginResponse)
async def employee_login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   AsyncSession = Depends(get_db),
):
    """
    Employee login endpoint for the NEF client app.
    Accepts form: username (email) + password.
    Returns an employee JWT valid for 12 hours.
    """
    result = await db.execute(
        text("""
            SELECT e.id::text AS id, e.email, e.name, e.department, e.role, e.status,
                   ea.password_hash, ea.is_active
            FROM employees e
            JOIN employee_auth ea ON ea.employee_id = e.id
            WHERE e.email = :email AND e.deleted_at IS NULL
        """),
        {"email": form.username},
    )
    row = result.fetchone()

    if not row or not row.is_active or row.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account inactive.",
        )

    if not _verify_password(form.password, row.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account inactive.",
        )

    # Update last_login
    await db.execute(
        text("UPDATE employee_auth SET last_login = NOW() WHERE employee_id::text = :id"),
        {"id": row.id},
    )
    await db.commit()

    token = _make_employee_token(row.id, row.email, row.name)
    return EmployeeLoginResponse(
        access_token=token,
        employee_id=row.id,
        name=row.name,
        email=row.email,
        department=row.department,
        role=row.role,
    )


@router.get("/me", response_model=EmployeeMeResponse)
async def employee_me(employee: dict = Depends(get_current_employee)):
    """Return the currently authenticated employee's profile."""
    return EmployeeMeResponse(
        id=employee["id"],
        email=employee["email"],
        name=employee["name"],
        department=employee.get("department"),
        role=employee.get("role"),
        status=employee["status"],
    )


@router.post("/set-password", status_code=200)
async def set_employee_password(
    body: SetPasswordRequest,
    db:   AsyncSession = Depends(get_db),
):
    """
    Admin/HR-facing endpoint to create or reset an employee's app password.
    This is called after an employee is created to provision their login.
    In production, combine with RBAC guard; for now protected at network layer.
    """
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    # Lookup employee
    result = await db.execute(
        text("SELECT id::text AS id FROM employees WHERE email = :email AND deleted_at IS NULL"),
        {"email": body.employee_email},
    )
    emp = result.fetchone()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    pw_hash = _hash_password(body.new_password)

    # Upsert into employee_auth
    await db.execute(
        text("""
            INSERT INTO employee_auth (id, employee_id, password_hash, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), :emp_id::uuid, :pw_hash, TRUE, NOW(), NOW())
            ON CONFLICT (employee_id)
            DO UPDATE SET password_hash = EXCLUDED.password_hash,
                          updated_at    = NOW(),
                          is_active     = TRUE
        """),
        {"emp_id": emp.id, "pw_hash": pw_hash},
    )
    await db.commit()
    return {"ok": True, "message": "Employee app password set successfully."}
