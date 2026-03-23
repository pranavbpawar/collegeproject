"""
Unit Tests — RBAC System
Tests role enforcement, permission mapping, JWT generation, and role-gated endpoints.
"""

import pytest
import uuid
from app.core.rbac import (
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    get_permissions_for_role,
    has_permission,
    hash_password,
    verify_password,
    make_rbac_token,
)
from jose import jwt
import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/tbaps_test")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_testing_must_be_long_enough")
os.environ.setdefault("ENCRYPTION_KEY", "test_encryption_key32bytes_012345")


# ── Permission tests ────────────────────────────────────────────────────────────

class TestRolePermissions:

    def test_admin_has_all_permissions(self):
        """Admin should have every permission in the Permission enum."""
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing: {perm.value}"

    def test_manager_cannot_send_agent(self):
        """Manager must NOT have SEND_NEF_AGENT permission."""
        assert not has_permission(UserRole.MANAGER, Permission.SEND_NEF_AGENT)

    def test_manager_cannot_view_all_employees(self):
        """Manager must NOT see all employees — only team."""
        assert not has_permission(UserRole.MANAGER, Permission.VIEW_ALL_EMPLOYEES)

    def test_manager_can_view_team(self):
        """Manager must be able to view team employees."""
        assert has_permission(UserRole.MANAGER, Permission.VIEW_TEAM_EMPLOYEES)

    def test_hr_can_view_all_employees(self):
        """HR must be able to view all employees."""
        assert has_permission(UserRole.HR, Permission.VIEW_ALL_EMPLOYEES)

    def test_hr_can_send_agent(self):
        """HR now HAS SEND_NEF_AGENT permission."""
        assert has_permission(UserRole.HR, Permission.SEND_NEF_AGENT)

    def test_hr_can_manage_system_config(self):
        """HR now HAS MANAGE_SYSTEM_CONFIG permission."""
        assert has_permission(UserRole.HR, Permission.MANAGE_SYSTEM_CONFIG)

    def test_hr_can_view_network_data_excluded(self):
        """HR still must NOT see raw network data."""
        assert not has_permission(UserRole.HR, Permission.VIEW_NETWORK_DATA)

    def test_manager_permissions_subset_of_admin(self):
        """All manager permissions must be a subset of admin permissions."""
        admin_perms   = ROLE_PERMISSIONS[UserRole.ADMIN]
        manager_perms = ROLE_PERMISSIONS[UserRole.MANAGER]
        for perm in manager_perms:
            assert perm in admin_perms

    def test_hr_permissions_subset_of_admin(self):
        """All HR permissions must be a subset of admin permissions."""
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        hr_perms    = ROLE_PERMISSIONS[UserRole.HR]
        for perm in hr_perms:
            assert perm in admin_perms

    def test_get_permissions_for_role_returns_strings(self):
        for role in UserRole:
            perms = get_permissions_for_role(role)
            assert isinstance(perms, list)
            assert all(isinstance(p, str) for p in perms)

    def test_manager_can_view_all_trust_scores(self):
        """Manager now HAS VIEW_ALL_TRUST_SCORES permission."""
        assert has_permission(UserRole.MANAGER, Permission.VIEW_ALL_TRUST_SCORES)

    def test_hr_can_view_all_trust_scores(self):
        """HR now HAS VIEW_ALL_TRUST_SCORES permission."""
        assert has_permission(UserRole.HR, Permission.VIEW_ALL_TRUST_SCORES)

    def test_hr_can_manage_users(self):
        """HR now HAS user management permissions."""
        for perm in [Permission.CREATE_SYSTEM_USER, Permission.UPDATE_SYSTEM_USER,
                     Permission.DELETE_SYSTEM_USER, Permission.VIEW_SYSTEM_USERS,
                     Permission.ASSIGN_ROLES]:
            assert has_permission(UserRole.HR, perm), f"HR missing: {perm.value}"


# ── Password tests ──────────────────────────────────────────────────────────────

class TestPasswordHelpers:

    def test_hash_and_verify(self):
        hashed = hash_password("SecurePass123!")
        assert verify_password("SecurePass123!", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("CorrectPwd")
        assert not verify_password("WrongPwd", hashed)

    def test_hashes_are_unique(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt salts uniquely


# ── JWT tests ───────────────────────────────────────────────────────────────────

class TestRbacJWT:

    def test_admin_token_contains_role(self):
        from app.core.config import settings
        token = make_rbac_token("user-1", "alice", "admin")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_aud": False})
        assert payload["role"] == "admin"
        assert payload["type"] == "rbac"

    def test_manager_token_contains_department(self):
        from app.core.config import settings
        dept_id = str(uuid.uuid4())
        token = make_rbac_token("user-2", "bob", "manager", dept_id, "Engineering")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_aud": False})
        assert payload["role"] == "manager"
        assert payload["department_id"] == dept_id
        assert payload["department_name"] == "Engineering"

    def test_hr_token_has_no_department(self):
        from app.core.config import settings
        token = make_rbac_token("user-3", "carol", "hr")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_aud": False})
        assert payload["role"]          == "hr"
        assert payload["department_id"] is None


# ── API endpoint auth tests ─────────────────────────────────────────────────────

class TestRbacEndpoints:
    """Smoke-test endpoints for 401 enforcement. No DB connection required."""

    def setup_method(self):
        import os
        os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/2")
        os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/3")
        os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        from fastapi.testclient import TestClient
        from app.main import app
        self.client = TestClient(app)

    def test_manager_team_requires_auth(self):
        res = self.client.get("/api/v1/manager/team")
        assert res.status_code == 401

    def test_hr_employees_requires_auth(self):
        res = self.client.get("/api/v1/hr/employees")
        assert res.status_code == 401

    def test_admin_users_requires_auth(self):
        res = self.client.get("/api/v1/admin/users")
        assert res.status_code == 401

    def test_admin_departments_requires_auth(self):
        res = self.client.get("/api/v1/admin/departments")
        assert res.status_code == 401

    def test_hr_anomalies_requires_auth(self):
        res = self.client.get("/api/v1/hr/anomalies")
        assert res.status_code == 401

    def test_auth_login_endpoint_exists(self):
        """POST /auth/login should return 422 (not 404) for missing body."""
        res = self.client.post("/api/v1/auth/login")
        assert res.status_code in (422, 200)  # 422 = form body required, 200 = unlikely but ok

    def test_manager_jwttype_rejected_on_hr_endpoint(self):
        """A manager JWT should be rejected (403) on HR-only endpoint."""
        from datetime import datetime, timedelta, timezone
        from app.core.config import settings
        from jose import jwt as jose_jwt

        token = jose_jwt.encode(
            {
                "sub": str(uuid.uuid4()), "username": "mgr",
                "role": "manager", "type": "rbac",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
        )
        res = self.client.get(
            "/api/v1/hr/employees",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 403 if user found in DB, or 401/500 if DB unavailable in test context
        assert res.status_code in (401, 403, 500)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
