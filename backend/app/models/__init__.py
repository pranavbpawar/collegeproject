"""
TBAPS SQLAlchemy Models
Database models matching PostgreSQL schema
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Enum, ForeignKey, TIMESTAMP, Text, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID, INET, BYTEA, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


__all__ = [
    "Employee", "SignalEvent", "BaselineProfile", "TrustScore", "OAuthToken",
    "AgentSendLog", "Department", "SystemUser",
    "EmployeeAuth", "ChatConversation", "ChatMessage", "ChatFile",
    "FileTransferAuditLog", "WorkSession",
]


class Employee(Base):
    """Employee model"""
    __tablename__ = "employees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    department = Column(String(100))
    role = Column(String(100))
    manager_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'))
    
    status = Column(
        Enum('active', 'inactive', 'offboarded', name='employee_status'),
        nullable=False,
        default='active'
    )
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(TIMESTAMP(timezone=True))
    
    extra_data = Column("metadata", JSONB, default={})
    
    # Relationships
    signal_events = relationship("SignalEvent", back_populates="employee")
    baseline_profiles = relationship("BaselineProfile", back_populates="employee")
    trust_scores = relationship("TrustScore", back_populates="employee")
    oauth_tokens = relationship("OAuthToken", back_populates="employee")


class SignalEvent(Base):
    """Signal event model (partitioned by month in PostgreSQL)"""
    __tablename__ = "signal_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False, index=True)
    
    signal_type = Column(
        Enum(
            'calendar_event', 'email_sent', 'email_received',
            'task_created', 'task_completed', 'meeting_attended',
            'code_commit', 'document_created', 'document_edited',
            name='signal_type'
        ),
        nullable=False,
        index=True
    )
    
    signal_value = Column(Float, nullable=False)
    extra_data = Column("metadata", JSONB, default={})
    source = Column(String(50), nullable=False)
    
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    employee = relationship("Employee", back_populates="signal_events")


class BaselineProfile(Base):
    """Baseline profile model"""
    __tablename__ = "baseline_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False, index=True)
    
    metric = Column(String(100), nullable=False)
    
    # Statistical values
    baseline_value = Column(Float, nullable=False)
    std_dev = Column(Float, nullable=False)
    p95 = Column(Float, nullable=False)
    p50 = Column(Float, nullable=False)
    p05 = Column(Float, nullable=False)
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)
    
    confidence = Column(Float, nullable=False)
    sample_size = Column(Integer, nullable=False)
    
    calculation_start = Column(TIMESTAMP(timezone=True), nullable=False)
    calculation_end = Column(TIMESTAMP(timezone=True), nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    employee = relationship("Employee", back_populates="baseline_profiles")
    
    __table_args__ = (
        {'schema': 'public'},
    )


class TrustScore(Base):
    """Trust score model (partitioned by month in PostgreSQL)"""
    __tablename__ = "trust_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False, index=True)
    
    outcome_score = Column(Float, nullable=False)
    behavioral_score = Column(Float, nullable=False)
    security_score = Column(Float, nullable=False)
    wellbeing_score = Column(Float, nullable=False)
    total_score = Column(Float, nullable=False)
    
    weights = Column(JSONB, default={'outcome': 0.3, 'behavioral': 0.3, 'security': 0.2, 'wellbeing': 0.2})
    
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    calculated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    employee = relationship("Employee", back_populates="trust_scores")


class OAuthToken(Base):
    """OAuth token model (encrypted)"""
    __tablename__ = "oauth_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False, index=True)
    
    service = Column(String(50), nullable=False)
    
    encrypted_token = Column(BYTEA, nullable=False)
    encrypted_refresh_token = Column(BYTEA)
    
    scope = Column(Text)
    token_type = Column(String(50), default='Bearer')
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    employee = relationship("Employee", back_populates="oauth_tokens")


class AgentSendLog(Base):
    """
    Audit log: tracks every admin-triggered NEF Agent email send.
    Table: agent_send_logs
    """
    __tablename__ = "agent_send_logs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id       = Column(String(255), nullable=False, index=True)
    employee_id    = Column(String(255), nullable=False, index=True)
    employee_email = Column(String(255), nullable=False)
    employee_name  = Column(String(255), nullable=True)
    status         = Column(String(50),  nullable=False)  # 'sent' | 'failed'
    error_detail   = Column(Text,        nullable=True)
    sent_at        = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)


# ── RBAC Models ────────────────────────────────────────────────────────────────

class Department(Base):
    """
    Department model — groups employees under named units.
    Managers are scoped to one department.
    """
    __tablename__ = "departments"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    system_users = relationship("SystemUser", back_populates="department")


class SystemUser(Base):
    """
    Unified platform user — covers Admin, Manager, and HR roles.
    Separate from the legacy admin_users table (kept for backwards-compat).
    """
    __tablename__ = "system_users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username      = Column(String(100), unique=True, nullable=False, index=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role          = Column(
        Enum('admin', 'manager', 'hr', name='system_user_role'),
        nullable=False,
        index=True,
    )
    department_id = Column(UUID(as_uuid=True), ForeignKey('departments.id'), nullable=True)
    is_active     = Column(Boolean, nullable=False, default=True)
    last_login    = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at    = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at    = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="system_users")


# ── Employee Auth (Client App Login) ───────────────────────────────────────────

class EmployeeAuth(Base):
    """
    Stores login credentials for employees accessing the NEF client app.
    Linked to the existing employees table via employee_id.
    """
    __tablename__ = "employee_auth"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    is_active   = Column(Boolean, nullable=False, default=True)
    last_login  = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at  = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at  = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Chat Models ─────────────────────────────────────────────────────────────────

class ChatConversation(Base):
    """
    A 1-to-1 conversation between an employee and a manager/HR user.
    """
    __tablename__ = "chat_conversations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id     = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False, index=True)
    # staff_user_id references system_users (manager / HR) or admin_users (admin)
    staff_user_id   = Column(UUID(as_uuid=True), nullable=False, index=True)
    staff_role      = Column(String(50), nullable=False)  # 'manager' | 'hr' | 'admin'
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    last_message_at = Column(TIMESTAMP(timezone=True), nullable=True)

    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    """
    A single message in a chat conversation (text or file attachment).
    """
    __tablename__ = "chat_messages"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('chat_conversations.id'), nullable=False, index=True)
    # sender_type identifies if the sender is an employee or staff
    sender_id       = Column(UUID(as_uuid=True), nullable=False, index=True)
    sender_type     = Column(String(20), nullable=False)  # 'employee' | 'staff'
    message_type    = Column(
        Enum('text', 'file', name='chat_message_type'),
        nullable=False,
        default='text'
    )
    content         = Column(Text, nullable=True)  # Text for text messages
    file_id         = Column(UUID(as_uuid=True), ForeignKey('chat_files.id'), nullable=True)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    is_read         = Column(Boolean, nullable=False, default=False)

    conversation    = relationship("ChatConversation", back_populates="messages")
    file            = relationship("ChatFile", foreign_keys=[file_id])


class ChatFile(Base):
    """
    Metadata for a file shared through the chat system.
    Actual file bytes are stored on-disk at storage_path.
    """
    __tablename__ = "chat_files"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('chat_conversations.id'), nullable=False, index=True)
    uploader_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    uploader_type   = Column(String(20), nullable=False)  # 'employee' | 'staff'
    original_name   = Column(String(255), nullable=False)
    mime_type       = Column(String(100), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    storage_path    = Column(Text, nullable=False)        # Server-side path (never exposed to client)
    checksum_sha256 = Column(String(64), nullable=True)   # SHA-256 of file content
    expires_at      = Column(TIMESTAMP(timezone=True), nullable=True)  # null = no expiry
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)


# ── Audit Log ───────────────────────────────────────────────────────────────────

class FileTransferAuditLog(Base):
    """
    Immutable audit trail for every file transfer action.
    """
    __tablename__ = "file_transfer_audit_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor_id    = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor_type  = Column(String(20), nullable=False)   # 'employee' | 'staff'
    action      = Column(String(20), nullable=False)   # 'upload' | 'download' | 'denied'
    file_name   = Column(String(255), nullable=False)
    file_size   = Column(BigInteger, nullable=True)
    ip_address  = Column(String(50), nullable=True)
    detail      = Column(Text, nullable=True)          # Error detail on denied
    timestamp   = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)


# ── Work Sessions ───────────────────────────────────────────────────────────────

class WorkSession(Base):
    """
    Tracks employee working hours via clock-in / clock-out.
    """
    __tablename__ = "work_sessions"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id       = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False, index=True)
    clock_in          = Column(TIMESTAMP(timezone=True), nullable=False)
    clock_out         = Column(TIMESTAMP(timezone=True), nullable=True)
    duration_minutes  = Column(Integer, nullable=True)     # null until clocked out
    notes             = Column(Text, nullable=True)
    created_at        = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
