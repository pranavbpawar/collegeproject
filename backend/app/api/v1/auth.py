"""
Admin Auth API
POST /api/v1/auth/admin/login   -> returns JWT access token
GET  /api/v1/auth/admin/me      -> returns current admin info
POST /api/v1/auth/admin/change-password
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings

router = APIRouter(prefix="/auth/admin", tags=["admin-auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/admin/login")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

# ── Models ─────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int  # seconds

class AdminInfo(BaseModel):
    id:         str
    username:   str
    email:      str
    last_login: Optional[str]

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_token(admin_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=12)
    return jwt.encode(
        {"sub": admin_id, "username": username, "exp": expire, "type": "admin"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        if payload.get("type") != "admin":
            raise creds_exc
        admin_id: str = payload.get("sub")
        if not admin_id:
            raise creds_exc
    except JWTError:
        raise creds_exc

    result = await db.execute(
        text("SELECT id, username, email, last_login FROM admin_users WHERE id = :id AND is_active = TRUE"),
        {"id": admin_id}
    )
    row = result.fetchone()
    if not row:
        raise creds_exc
    return dict(row._mapping)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def admin_login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login with username + password. Returns a 12-hour JWT."""
    result = await db.execute(
        text("SELECT id, password_hash FROM admin_users WHERE username = :u AND is_active = TRUE"),
        {"u": form.username}
    )
    row = result.fetchone()
    if not row or not _verify_password(form.password, row.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Update last_login
    await db.execute(
        text("UPDATE admin_users SET last_login = NOW() WHERE id = :id"),
        {"id": str(row.id)}
    )
    await db.commit()

    token = _make_token(str(row.id), form.username)
    return TokenResponse(access_token=token, expires_in=43200)


@router.get("/me", response_model=AdminInfo)
async def admin_me(admin: dict = Depends(get_current_admin)):
    """Return current admin info."""
    return AdminInfo(
        id=str(admin["id"]),
        username=admin["username"],
        email=admin["email"],
        last_login=str(admin["last_login"]) if admin.get("last_login") else None,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change the current admin's password."""
    result = await db.execute(
        text("SELECT password_hash FROM admin_users WHERE id = :id"),
        {"id": str(admin["id"])}
    )
    row = result.fetchone()
    if not row or not _verify_password(body.current_password, row.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    new_hash = _hash_password(body.new_password)
    await db.execute(
        text("UPDATE admin_users SET password_hash = :h WHERE id = :id"),
        {"h": new_hash, "id": str(admin["id"])}
    )
    await db.commit()
    return {"ok": True, "message": "Password changed successfully"}
