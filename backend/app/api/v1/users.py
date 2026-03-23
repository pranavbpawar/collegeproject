"""
User Creation & Common Resources API
Accessible to Admin, Manager, and HR.
Enforces role-based boundaries on data visibility and creation.
"""

import uuid
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_rbac_user, UserRole
from app.api.v1.admin_send_agent import _build_download_urls
from app.services.email_service import send_agent_email

router = APIRouter(prefix="/user", tags=["user-common"])

class CreateEmployeeRequest(BaseModel):
    name:       str
    email:      EmailStr
    department: str
    send_email: bool = True

@router.get("/departments")
async def get_departments(
    user: dict = Depends(get_current_rbac_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all departments.
    Available to Admin, HR, and Manager (needed for HR dropdown, and general lookup).
    """
    result = await db.execute(text("SELECT id::text AS id, name FROM departments ORDER BY name"))
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/create-employee", status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: CreateEmployeeRequest,
    user: dict = Depends(get_current_rbac_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Employee creation.
    - HR & Admin: Can assign any department.
    - Manager: Can only assign their own department.
    """
    request_role = UserRole(user["role"])
    
    # ── Role Enforcement ──
    if request_role == UserRole.MANAGER:
        manager_dept = user.get("department_name") or ""
        if (manager_dept.strip().lower() != body.department.strip().lower()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Managers can only create employees in their own department ({manager_dept})"
            )
    
    new_id = str(uuid.uuid4())

    try:
        # Check if a soft-deleted employee with same email exists — reactivate
        existing = await db.execute(
            text("SELECT id::text FROM employees WHERE email = :email AND deleted_at IS NOT NULL"),
            {"email": body.email}
        )
        existing_row = existing.fetchone()

        if existing_row:
            new_id = existing_row[0]
            await db.execute(
                text("""
                    UPDATE employees
                    SET name       = :name,
                        department = :dept,
                        status     = 'active',
                        deleted_at = NULL,
                        updated_at = NOW()
                    WHERE id = CAST(:id AS UUID)
                """),
                {"name": body.name, "dept": body.department, "id": new_id}
            )
        else:
            # Check uniqueness
            dup = await db.execute(
                text("SELECT 1 FROM employees WHERE email=:email AND deleted_at IS NULL"), 
                {"email": body.email}
            )
            if dup.fetchone():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
            
            # Insert new
            await db.execute(
                text("""
                    INSERT INTO employees
                        (id, name, email, department, status, created_at, updated_at)
                    VALUES
                        (:id, :name, :email, :dept, 'active', NOW(), NOW())
                """),
                {
                    "id":    new_id,
                    "name":  body.name,
                    "email": body.email,
                    "dept":  body.department,
                },
            )

        # Audit log linking the creator's ID
        await db.execute(
            text("""
                INSERT INTO audit_logs
                    (action, resource_type, resource_id, changes)
                VALUES
                    ('CREATE', 'employee', :new_id, CAST(:changes AS JSONB))
            """),
            {
                "new_id":  new_id,
                "changes": json.dumps({
                    "created_by": user["id"],
                    "creator_role": user["role"],
                    "admin_id": user["id"] if user["role"] == "admin" else None
                })
            }
        )
        await db.commit()

        # Fire email if requested
        if body.send_email:
            linux_url, windows_url = _build_download_urls(body.name)
            asyncio.create_task(
                send_agent_email(
                    to_email=body.email,
                    to_name=body.name,
                    employee_id=new_id,
                    download_url_linux=linux_url,
                    download_url_windows=windows_url,
                )
            )

        return {"id": new_id, "message": "Employee created successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        if "unique" in str(e).lower() or "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail="Email already exists")
        raise HTTPException(status_code=500, detail=str(e))
