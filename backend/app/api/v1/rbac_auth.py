"""
TBAPS — Unified RBAC Authentication
POST /api/v1/auth/login          → JWT for admin, manager, or hr
GET  /api/v1/auth/me             → current user + role + permissions
POST /api/v1/auth/change-password
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import (
    get_current_rbac_user,
    hash_password,
    make_rbac_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["rbac-auth"])


# ── Response models ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token:    str
    token_type:      str = "bearer"
    expires_in:      int = 43200
    role:            str
    department_id:   Optional[str]
    department_name: Optional[str]
    permissions:     list[str]


class MeResponse(BaseModel):
    id:              str
    username:        str
    email:           str
    role:            str
    department_id:   Optional[str]
    department_name: Optional[str]
    permissions:     list[str]
    last_login:      Optional[str]


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def unified_login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   AsyncSession = Depends(get_db),
):
    """
    Unified login for Admin, Manager, and HR.
    Accepts form-encoded: username + password.
    Returns JWT containing role and department claims.
    """
    result = await db.execute(
        text("""
            SELECT su.id::text AS id, su.username, su.email,
                   su.password_hash, su.role, su.is_active,
                   su.department_id::text AS department_id,
                   d.name AS department_name
            FROM system_users su
            LEFT JOIN departments d ON su.department_id = d.id
            WHERE (su.username = :u OR su.email = :u) AND su.is_active = TRUE
        """),
        {"u": form.username},
    )
    row = result.fetchone()
    if not row:
        print(f"DEBUG LOGIN: No row found for {form.username}")
    elif not verify_password(form.password, row.password_hash):
        print(f"DEBUG LOGIN: Password mismatch for {form.username}. Provided: {form.password}")
    
    if not row or not verify_password(form.password, row.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Update last_login
    await db.execute(
        text("UPDATE system_users SET last_login = NOW() WHERE id::text = :id"),
        {"id": row.id},
    )
    await db.commit()

    from app.core.rbac import get_permissions_for_role, UserRole
    perms = get_permissions_for_role(UserRole(row.role))
    token = make_rbac_token(
        user_id=row.id,
        username=row.username,
        role=row.role,
        department_id=row.department_id,
        department_name=row.department_name,
    )

    return TokenResponse(
        access_token=token,
        role=row.role,
        department_id=row.department_id,
        department_name=row.department_name,
        permissions=perms,
    )


@router.get("/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_rbac_user), db: AsyncSession = Depends(get_db)):
    """Return current user's profile including role and permissions."""
    result = await db.execute(
        text("SELECT last_login FROM system_users WHERE id::text = :id"),
        {"id": user["id"]},
    )
    row = result.fetchone()
    return MeResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user["role"],
        department_id=user.get("department_id"),
        department_name=user.get("department_name"),
        permissions=user["permissions"],
        last_login=str(row.last_login) if row and row.last_login else None,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: dict = Depends(get_current_rbac_user),
    db:   AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    result = await db.execute(
        text("SELECT password_hash FROM system_users WHERE id::text = :id"),
        {"id": user["id"]},
    )
    row = result.fetchone()
    if not row or not verify_password(body.current_password, row.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    new_hash = hash_password(body.new_password)
    await db.execute(
        text("UPDATE system_users SET password_hash = :h, updated_at = NOW() WHERE id::text = :id"),
        {"h": new_hash, "id": user["id"]},
    )
    await db.commit()
    return {"ok": True, "message": "Password changed successfully"}
