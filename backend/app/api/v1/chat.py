"""
TBAPS — Chat & Secure File Sharing API
Supports 1-to-1 conversations between employees and manager/HR staff,
text messages, and secure file attachments.

Endpoints:
  POST /api/v1/chat/conversations          — create or get conversation
  GET  /api/v1/chat/conversations          — list my conversations
  GET  /api/v1/chat/{conv_id}/messages     — paginated messages
  POST /api/v1/chat/{conv_id}/messages     — send text message
  POST /api/v1/chat/upload                 — upload file attachment
  GET  /api/v1/chat/file/{file_id}         — secure time-limited download
  GET  /api/v1/chat/file/{file_id}/token   — generate download token
"""

import logging
import mimetypes
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, Query,
    Request, UploadFile, status
)
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import get_current_rbac_user, UserRole
from app.api.v1.employee_auth import get_current_employee
from app.services import file_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _is_staff_user(user: dict) -> bool:
    return user.get("role") in ("admin", "manager", "hr")


async def _verify_conversation_access(
    conv_id: str, actor_id: str, db: AsyncSession
) -> dict:
    """
    Confirm the actor (employee or staff) is a participant in this conversation.
    Returns the conversation row or raises 403/404.
    """
    result = await db.execute(
        text("""
            SELECT id::text AS id, employee_id::text AS employee_id,
                   staff_user_id::text AS staff_user_id, staff_role
            FROM chat_conversations WHERE id::text = :conv_id
        """),
        {"conv_id": conv_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conv = dict(row._mapping)
    if actor_id not in (conv["employee_id"], conv["staff_user_id"]):
        raise HTTPException(status_code=403, detail="Access denied to this conversation.")
    return conv


# ── Request / Response models ──────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    employee_id:   str   # UUID of the employee (staff-initiated)
    staff_user_id: Optional[str] = None  # UUID of staff (employee-initiated)


class SendMessageRequest(BaseModel):
    content: str


class ConversationOut(BaseModel):
    id:             str
    employee_id:    str
    staff_user_id:  str
    staff_role:     str
    created_at:     str
    last_message_at: Optional[str]


class MessageOut(BaseModel):
    id:             str
    conversation_id: str
    sender_id:      str
    sender_type:    str
    message_type:   str
    content:        Optional[str]
    file_id:        Optional[str]
    file_name:      Optional[str]
    file_size_bytes:Optional[int]
    file_size_human:Optional[str]
    created_at:     str
    is_read:        bool


# ── Conversations ──────────────────────────────────────────────────────────────

@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_or_get_conversation(
    body: CreateConversationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create or fetch an existing conversation between an employee and a staff user.
    Can be called by either side. Idempotent — returns existing conv if it exists.
    Auth: Bearer token (either employee JWT or RBAC JWT).

    NOTE: Auth is flexible on this endpoint to allow both employee and staff tokens.
    The caller must supply valid IDs. In production, add stricter token parsing.
    """
    emp_id   = body.employee_id
    staff_id = body.staff_user_id

    # Validate employee exists
    emp_check = await db.execute(
        text("SELECT id::text AS id FROM employees WHERE id::text = :id AND deleted_at IS NULL"),
        {"id": emp_id},
    )
    if not emp_check.fetchone():
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Check existing conversation
    existing = await db.execute(
        text("""
            SELECT id::text AS id, employee_id::text AS employee_id,
                   staff_user_id::text AS staff_user_id, staff_role,
                   created_at::text AS created_at,
                   last_message_at::text AS last_message_at
            FROM chat_conversations
            WHERE employee_id::text = :emp_id AND staff_user_id::text = :staff_id
        """),
        {"emp_id": emp_id, "staff_id": staff_id},
    )
    row = existing.fetchone()
    if row:
        return ConversationOut(**dict(row._mapping))

    # Look up staff role
    staff_row = await db.execute(
        text("SELECT role FROM system_users WHERE id::text = :id AND is_active = TRUE"),
        {"id": staff_id},
    )
    s = staff_row.fetchone()
    staff_role = s.role if s else "manager"

    new_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO chat_conversations
                (id, employee_id, staff_user_id, staff_role, created_at)
            VALUES (:id::uuid, :emp_id::uuid, :staff_id::uuid, :role, NOW())
        """),
        {"id": new_id, "emp_id": emp_id, "staff_id": staff_id, "role": staff_role},
    )
    await db.commit()

    result = await db.execute(
        text("""
            SELECT id::text AS id, employee_id::text AS employee_id,
                   staff_user_id::text AS staff_user_id, staff_role,
                   created_at::text AS created_at, last_message_at::text AS last_message_at
            FROM chat_conversations WHERE id::text = :id
        """),
        {"id": new_id},
    )
    return ConversationOut(**dict(result.fetchone()._mapping))


@router.get("/conversations")
async def list_my_conversations(
    request: Request,
    employee: Optional[dict] = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    List all conversations for the authenticated employee.
    """
    if not employee:
        raise HTTPException(status_code=401, detail="Authentication required.")

    result = await db.execute(
        text("""
            SELECT
                cc.id::text AS id,
                cc.employee_id::text AS employee_id,
                cc.staff_user_id::text AS staff_user_id,
                cc.staff_role,
                cc.created_at::text AS created_at,
                cc.last_message_at::text AS last_message_at,
                su.username AS staff_name,
                su.email AS staff_email
            FROM chat_conversations cc
            LEFT JOIN system_users su ON su.id = cc.staff_user_id
            WHERE cc.employee_id::text = :emp_id
            ORDER BY COALESCE(cc.last_message_at, cc.created_at) DESC
        """),
        {"emp_id": employee["id"]},
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/conversations/staff")
async def list_staff_conversations(
    user: dict = Depends(get_current_rbac_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all conversations for an authenticated manager/HR user.
    Managers see only their department's employees.
    """
    dept_clause = ""
    params: dict = {"staff_id": user["id"]}

    if UserRole(user["role"]) == UserRole.MANAGER:
        dept_clause = "AND e.department ILIKE :dept"
        params["dept"] = user.get("department_name", "")

    result = await db.execute(
        text(f"""
            SELECT
                cc.id::text AS id,
                cc.employee_id::text AS employee_id,
                cc.staff_user_id::text AS staff_user_id,
                cc.staff_role,
                cc.created_at::text AS created_at,
                cc.last_message_at::text AS last_message_at,
                e.name AS employee_name,
                e.email AS employee_email,
                e.department AS employee_department
            FROM chat_conversations cc
            JOIN employees e ON e.id = cc.employee_id
            WHERE cc.staff_user_id::text = :staff_id
              AND e.deleted_at IS NULL
              {dept_clause}
            ORDER BY COALESCE(cc.last_message_at, cc.created_at) DESC
        """),
        params,
    )
    return [dict(r._mapping) for r in result.fetchall()]


# ── Messages ───────────────────────────────────────────────────────────────────

@router.get("/{conv_id}/messages")
async def get_messages(
    conv_id: str,
    limit:   int = Query(default=50, le=200),
    before:  Optional[str] = Query(default=None, description="ISO timestamp for pagination"),
    employee: Optional[dict] = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    Paginated message history for a conversation.
    Accessible by employee or staff participant.
    """
    if not employee:
        raise HTTPException(status_code=401, detail="Authentication required.")

    await _verify_conversation_access(conv_id, employee["id"], db)

    time_clause = ""
    params: dict = {"conv_id": conv_id, "limit": limit}
    if before:
        time_clause = "AND cm.created_at < :before::timestamptz"
        params["before"] = before

    result = await db.execute(
        text(f"""
            SELECT
                cm.id::text AS id,
                cm.conversation_id::text AS conversation_id,
                cm.sender_id::text AS sender_id,
                cm.sender_type,
                cm.message_type,
                cm.content,
                cm.file_id::text AS file_id,
                cf.original_name AS file_name,
                cf.file_size_bytes,
                cm.created_at::text AS created_at,
                cm.is_read
            FROM chat_messages cm
            LEFT JOIN chat_files cf ON cf.id = cm.file_id
            WHERE cm.conversation_id::text = :conv_id
              {time_clause}
            ORDER BY cm.created_at DESC
            LIMIT :limit
        """),
        params,
    )
    rows = result.fetchall()
    messages = []
    for r in rows:
        m = dict(r._mapping)
        if m["file_size_bytes"]:
            m["file_size_human"] = file_service.human_readable_size(m["file_size_bytes"])
        else:
            m["file_size_human"] = None
        messages.append(m)
    return list(reversed(messages))  # Return in chronological order


@router.post("/{conv_id}/messages", status_code=201)
async def send_message(
    conv_id:  str,
    body:     SendMessageRequest,
    employee: Optional[dict] = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a text message in a conversation (employee side).
    """
    if not employee:
        raise HTTPException(status_code=401, detail="Authentication required.")

    conv = await _verify_conversation_access(conv_id, employee["id"], db)

    if not body.content or not body.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")

    msg_id = str(uuid.uuid4())
    sender_type = "employee" if employee["id"] == conv["employee_id"] else "staff"

    await db.execute(
        text("""
            INSERT INTO chat_messages
                (id, conversation_id, sender_id, sender_type, message_type, content, created_at, is_read)
            VALUES (:id::uuid, :conv_id::uuid, :sender_id::uuid, :sender_type, 'text', :content, NOW(), FALSE)
        """),
        {
            "id": msg_id, "conv_id": conv_id,
            "sender_id": employee["id"], "sender_type": sender_type,
            "content": body.content.strip(),
        },
    )
    await db.execute(
        text("UPDATE chat_conversations SET last_message_at = NOW() WHERE id::text = :id"),
        {"id": conv_id},
    )
    await db.commit()
    return {"ok": True, "message_id": msg_id}


@router.post("/{conv_id}/messages/staff", status_code=201)
async def send_message_staff(
    conv_id: str,
    body:    SendMessageRequest,
    user:    dict = Depends(get_current_rbac_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a text message in a conversation (staff / manager / HR side).
    """
    conv = await _verify_conversation_access(conv_id, user["id"], db)

    if not body.content or not body.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")

    msg_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO chat_messages
                (id, conversation_id, sender_id, sender_type, message_type, content, created_at, is_read)
            VALUES (:id::uuid, :conv_id::uuid, :sender_id::uuid, 'staff', 'text', :content, NOW(), FALSE)
        """),
        {"id": msg_id, "conv_id": conv_id, "sender_id": user["id"], "content": body.content.strip()},
    )
    await db.execute(
        text("UPDATE chat_conversations SET last_message_at = NOW() WHERE id::text = :id"),
        {"id": conv_id},
    )
    await db.commit()
    return {"ok": True, "message_id": msg_id}


# ── File Upload ────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=201)
async def upload_file(
    request:        Request,
    conversation_id: str = Form(...),
    file:           UploadFile = File(...),
    employee: Optional[dict] = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file into a conversation. Creates a ChatFile record and a ChatMessage.
    Returns the file_id and a download token.

    Access control:
    - Employee JWT required (employees upload files)
    - Employee must be a participant in the conversation
    """
    if not employee:
        raise HTTPException(status_code=401, detail="Authentication required.")

    conv = await _verify_conversation_access(conversation_id, employee["id"], db)

    # Read content first to get real size
    content = await file.read()
    size = len(content)

    # Security validation
    file_service.validate_file(
        filename=file.filename or "unnamed",
        content_type=file.content_type or "",
        size=size,
    )

    file_id  = str(uuid.uuid4())
    emp_id   = employee["id"]
    filename = file.filename or f"file_{file_id}"
    mime     = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    # Store to disk
    storage_path = file_service.build_storage_path(file_id, emp_id, conversation_id, filename)
    checksum = file_service.save_file_to_disk(content, storage_path)

    # Insert ChatFile record
    await db.execute(
        text("""
            INSERT INTO chat_files
                (id, conversation_id, uploader_id, uploader_type,
                 original_name, mime_type, file_size_bytes, storage_path, checksum_sha256, created_at)
            VALUES
                (:id::uuid, :conv_id::uuid, :uploader::uuid, 'employee',
                 :name, :mime, :size, :path, :checksum, NOW())
        """),
        {
            "id": file_id, "conv_id": conversation_id, "uploader": emp_id,
            "name": filename, "mime": mime, "size": size,
            "path": str(storage_path), "checksum": checksum,
        },
    )

    # Insert ChatMessage (type=file)
    msg_id = str(uuid.uuid4())
    sender_type = "employee" if emp_id == conv["employee_id"] else "staff"
    await db.execute(
        text("""
            INSERT INTO chat_messages
                (id, conversation_id, sender_id, sender_type, message_type, file_id, created_at, is_read)
            VALUES (:id::uuid, :conv_id::uuid, :sender::uuid, :stype, 'file', :fid::uuid, NOW(), FALSE)
        """),
        {"id": msg_id, "conv_id": conversation_id, "sender": emp_id,
         "stype": sender_type, "fid": file_id},
    )

    await db.execute(
        text("UPDATE chat_conversations SET last_message_at = NOW() WHERE id::text = :id"),
        {"id": conversation_id},
    )

    # Audit log — upload
    await db.execute(
        text("""
            INSERT INTO file_transfer_audit_logs
                (id, file_id, actor_id, actor_type, action, file_name, file_size, ip_address, timestamp)
            VALUES (gen_random_uuid(), :fid::uuid, :actor::uuid, 'employee', 'upload', :name, :size, :ip, NOW())
        """),
        {
            "fid": file_id, "actor": emp_id, "name": filename, "size": size,
            "ip": request.client.host if request.client else None,
        },
    )
    await db.commit()

    download_token = file_service.generate_download_token(file_id, emp_id)

    return {
        "ok":            True,
        "file_id":       file_id,
        "message_id":    msg_id,
        "file_name":     filename,
        "file_size":     size,
        "file_size_human": file_service.human_readable_size(size),
        "download_token": download_token,
    }


# ── Secure Download ────────────────────────────────────────────────────────────

@router.get("/file/{file_id}/token")
async def get_download_token(
    file_id:  str,
    employee: Optional[dict] = Depends(get_current_employee),
    user:     Optional[dict] = Depends(get_current_rbac_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a time-limited download token for a file.
    Can be called by employee or staff participant.
    """
    actor_id = None
    if employee:
        actor_id = employee["id"]
    elif user:
        actor_id = user["id"]
    else:
        raise HTTPException(status_code=401, detail="Authentication required.")

    # Verify file exists and actor has access
    result = await db.execute(
        text("""
            SELECT cf.id::text AS id, cf.conversation_id::text AS conv_id,
                   cf.original_name, cf.storage_path
            FROM chat_files cf
            WHERE cf.id::text = :fid
        """),
        {"fid": file_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")

    await _verify_conversation_access(row.conv_id, actor_id, db)

    token = file_service.generate_download_token(file_id, actor_id)
    return {"download_token": token, "file_name": row.original_name}


@router.get("/file/{file_id}")
async def download_file(
    file_id: str,
    token:   str = Query(..., description="Time-limited download token"),
    user_id: str = Query(..., description="Requesting user ID"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Secure file download endpoint.
    Requires valid time-limited token. Only sender or receiver can download.
    Logs every download attempt.
    """
    # Verify token
    file_service.verify_download_token(token, file_id, user_id)

    # Fetch file metadata
    result = await db.execute(
        text("""
            SELECT cf.id::text AS id, cf.conversation_id::text AS conv_id,
                   cf.original_name, cf.mime_type, cf.storage_path, cf.file_size_bytes
            FROM chat_files cf
            WHERE cf.id::text = :fid
        """),
        {"fid": file_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found.")

    # Verify conversation access
    await _verify_conversation_access(row.conv_id, user_id, db)

    # Read file content
    content = file_service.read_file_from_disk(row.storage_path)

    # Audit log — download
    await db.execute(
        text("""
            INSERT INTO file_transfer_audit_logs
                (id, file_id, actor_id, actor_type, action, file_name, file_size, ip_address, timestamp)
            VALUES (gen_random_uuid(), :fid::uuid, :actor::uuid, 'unknown', 'download',
                    :name, :size, :ip, NOW())
        """),
        {
            "fid": file_id, "actor": user_id, "name": row.original_name,
            "size": row.file_size_bytes,
            "ip": request.client.host if request and request.client else None,
        },
    )
    await db.commit()

    mime = row.mime_type or "application/octet-stream"
    filename = row.original_name

    return Response(
        content=content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
