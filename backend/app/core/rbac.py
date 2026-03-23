"""
TBAPS — Core RBAC Module
Role definitions, permission sets, and FastAPI dependency guards.

Usage:
    from app.core.rbac import require_admin, require_hr_or_admin, get_current_rbac_user

    @router.get("/secret")
    async def secret(user: dict = Depends(require_admin())):
        ...
"""

import logging
from enum import Enum
from typing import Optional, Set
from functools import lru_cache

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Role Enum ──────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN   = "admin"
    MANAGER = "manager"
    HR      = "hr"


# ── Permission Registry ────────────────────────────────────────────────────────

class Permission(str, Enum):
    # Employee management
    CREATE_EMPLOYEE         = "create_employee"
    UPDATE_EMPLOYEE         = "update_employee"
    DELETE_EMPLOYEE         = "delete_employee"
    VIEW_ALL_EMPLOYEES      = "view_all_employees"
    VIEW_TEAM_EMPLOYEES     = "view_team_employees"

    # User / role management
    CREATE_SYSTEM_USER      = "create_system_user"
    UPDATE_SYSTEM_USER      = "update_system_user"
    DELETE_SYSTEM_USER      = "delete_system_user"
    VIEW_SYSTEM_USERS       = "view_system_users"
    ASSIGN_ROLES            = "assign_roles"
    MANAGE_DEPARTMENTS      = "manage_departments"

    # Monitoring & trust
    VIEW_ALL_TRUST_SCORES   = "view_all_trust_scores"
    VIEW_TEAM_TRUST_SCORES  = "view_team_trust_scores"
    VIEW_TRUST_TRENDS       = "view_trust_trends"
    VIEW_ALL_ACTIVITY       = "view_all_activity"
    VIEW_TEAM_ACTIVITY      = "view_team_activity"
    VIEW_BEHAVIORAL_DATA    = "view_behavioral_data"

    # Alerts & anomalies
    VIEW_ALL_ANOMALIES      = "view_all_anomalies"
    VIEW_TEAM_ANOMALIES     = "view_team_anomalies"

    # Compliance
    VIEW_COMPLIANCE_LOGS    = "view_compliance_logs"
    VIEW_AUDIT_LOGS         = "view_audit_logs"

    # System controls
    MANAGE_SYSTEM_CONFIG    = "manage_system_config"
    VIEW_SYSTEM_CONFIG      = "view_system_config"
    SEND_NEF_AGENT          = "send_nef_agent"

    # Network / low-level (admin only)
    VIEW_NETWORK_DATA       = "view_network_data"


# ── Role → Permission Mapping ──────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: set(Permission),  # All permissions

    UserRole.MANAGER: {
        Permission.VIEW_TEAM_EMPLOYEES,
        Permission.VIEW_TEAM_TRUST_SCORES,
        Permission.VIEW_ALL_TRUST_SCORES,   # ← added
        Permission.VIEW_TEAM_ACTIVITY,
        Permission.VIEW_TEAM_ANOMALIES,
    },

    UserRole.HR: {
        # Employees & behavioural
        Permission.VIEW_ALL_EMPLOYEES,
        Permission.VIEW_BEHAVIORAL_DATA,
        Permission.VIEW_ALL_ANOMALIES,
        Permission.VIEW_COMPLIANCE_LOGS,
        Permission.VIEW_TRUST_TRENDS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.VIEW_ALL_TRUST_SCORES,   # ← added

        # Agent distribution
        Permission.SEND_NEF_AGENT,           # ← added

        # System config
        Permission.MANAGE_SYSTEM_CONFIG,     # ← added
        Permission.VIEW_SYSTEM_CONFIG,

        # User / role management
        Permission.CREATE_SYSTEM_USER,       # ← added
        Permission.UPDATE_SYSTEM_USER,       # ← added
        Permission.DELETE_SYSTEM_USER,       # ← added
        Permission.VIEW_SYSTEM_USERS,        # ← added
        Permission.ASSIGN_ROLES,             # ← added
    },
}



def get_permissions_for_role(role: UserRole) -> list[str]:
    """Return list of permission strings for the given role."""
    return [p.value for p in ROLE_PERMISSIONS.get(role, set())]


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


# ── Password Helpers ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── JWT Helpers ────────────────────────────────────────────────────────────────

def make_rbac_token(
    user_id: str,
    username: str,
    role: str,
    department_id: Optional[str] = None,
    department_name: Optional[str] = None,
) -> str:
    """Create a role-aware JWT with 12-hour expiry."""
    from datetime import datetime, timedelta, timezone
    expire = datetime.now(timezone.utc) + timedelta(hours=12)
    payload = {
        "sub":             user_id,
        "username":        username,
        "role":            role,
        "department_id":   department_id,
        "department_name": department_name,
        "type":            "rbac",
        "exp":             expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── Auth Dependency ────────────────────────────────────────────────────────────

async def get_current_rbac_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    FastAPI dependency — decode RBAC JWT and return the current user dict.
    Raises 401 on invalid/expired token or unknown user.
    """
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        token_type = payload.get("type")
        if token_type not in ("rbac", "admin"):
            raise creds_exc
        user_id: str = payload.get("sub")
        if not user_id:
            raise creds_exc
    except JWTError:
        raise creds_exc

    if token_type == "admin":
        result = await db.execute(
            text("SELECT id::text AS id, username, email FROM admin_users WHERE id::text = :id AND is_active = TRUE"),
            {"id": user_id},
        )
        row = result.fetchone()
        if not row:
            raise creds_exc
        
        user = dict(row._mapping)
        user["role"] = "admin"
        user["permissions"] = get_permissions_for_role(UserRole.ADMIN)
        return user

    # Otherwise, token is 'rbac', check system_users
    result = await db.execute(
        text("""
            SELECT su.id::text AS id, su.username, su.email, su.role,
                   su.department_id::text AS department_id,
                   su.is_active, d.name AS department_name
            FROM system_users su
            LEFT JOIN departments d ON su.department_id = d.id
            WHERE su.id::text = :id AND su.is_active = TRUE
        """),
        {"id": user_id},
    )
    row = result.fetchone()
    if not row:
        raise creds_exc

    user = dict(row._mapping)
    user["permissions"] = get_permissions_for_role(UserRole(user["role"]))
    return user


# ── Permission Guard Factories ─────────────────────────────────────────────────

def require_role(*allowed_roles: UserRole):
    """
    FastAPI dependency factory — requires one of the specified roles.

    Usage:
        @router.get("/admin-only")
        async def admin_only(user = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def _guard(user: dict = Depends(get_current_rbac_user)) -> dict:
        if UserRole(user["role"]) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in allowed_roles]}. "
                       f"Your role: {user['role']}",
            )
        return user
    return _guard


def require_admin():
    """Shorthand: admin only."""
    return require_role(UserRole.ADMIN)


def require_manager_or_admin():
    """Shorthand: manager or admin."""
    return require_role(UserRole.ADMIN, UserRole.MANAGER)


def require_hr_or_admin():
    """Shorthand: HR or admin."""
    return require_role(UserRole.ADMIN, UserRole.HR)


def require_any_staff():
    """Shorthand: any authenticated platform user."""
    return require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.HR)


def check_department_access(user: dict, department: Optional[str]) -> bool:
    """
    Returns True if the user is allowed to access the given department:
    - Admin: always True
    - Manager: only if department matches their own
    """
    role = UserRole(user["role"])
    if role == UserRole.ADMIN:
        return True
    if role == UserRole.MANAGER:
        return user.get("department_name", "").lower() == (department or "").lower()
    return False  # HR uses HR-specific endpoints, not this guard
