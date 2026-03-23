"""
Migration: Add chat, file sharing, employee auth, and work session tables.

Revision ID: 2024_chat_fileshare_v1
Revises: (set to current head)
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision      = "2024_chat_fileshare_v1"
down_revision = "001_initial_schema"   # chains after initial schema

branch_labels = None
depends_on    = None


def upgrade():
    # ── employee_auth ──────────────────────────────────────────────────────────
    op.create_table(
        "employee_auth",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("employee_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False, unique=True),
        sa.Column("password_hash",sa.Text(), nullable=False),
        sa.Column("is_active",    sa.Boolean(), nullable=False, server_default="TRUE"),
        sa.Column("last_login",   sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at",   sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",   sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_employee_auth_employee_id", "employee_auth", ["employee_id"])

    # ── chat_conversations ─────────────────────────────────────────────────────
    op.create_table(
        "chat_conversations",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("employee_id",     postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("staff_user_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_role",      sa.String(50), nullable=False),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_message_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_chat_conversations_employee_id",   "chat_conversations", ["employee_id"])
    op.create_index("ix_chat_conversations_staff_user_id", "chat_conversations", ["staff_user_id"])

    # ── chat_message_type enum ─────────────────────────────────────────────────
    chat_msg_type = postgresql.ENUM("text", "file", name="chat_message_type", create_type=True)
    chat_msg_type.create(op.get_bind(), checkfirst=True)

    # ── chat_files ─────────────────────────────────────────────────────────────
    op.create_table(
        "chat_files",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_conversations.id"), nullable=False),
        sa.Column("uploader_id",     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploader_type",   sa.String(20), nullable=False),
        sa.Column("original_name",   sa.String(255), nullable=False),
        sa.Column("mime_type",       sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path",    sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("expires_at",      sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_chat_files_conversation_id", "chat_files", ["conversation_id"])
    op.create_index("ix_chat_files_uploader_id",     "chat_files", ["uploader_id"])

    # ── chat_messages ──────────────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_conversations.id"), nullable=False),
        sa.Column("sender_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_type",     sa.String(20), nullable=False),
        sa.Column("message_type",    sa.Enum("text", "file", name="chat_message_type", create_type=False), nullable=False, server_default="text"),
        sa.Column("content",         sa.Text(), nullable=True),
        sa.Column("file_id",         postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_files.id"), nullable=True),
        sa.Column("created_at",      sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("is_read",         sa.Boolean(), nullable=False, server_default="FALSE"),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_index("ix_chat_messages_sender_id",       "chat_messages", ["sender_id"])

    # ── file_transfer_audit_logs ───────────────────────────────────────────────
    op.create_table(
        "file_transfer_audit_logs",
        sa.Column("id",        postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("file_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id",  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type",sa.String(20), nullable=False),
        sa.Column("action",    sa.String(20), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("ip_address",sa.String(50), nullable=True),
        sa.Column("detail",    sa.Text(), nullable=True),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ftaudit_file_id",  "file_transfer_audit_logs", ["file_id"])
    op.create_index("ix_ftaudit_actor_id", "file_transfer_audit_logs", ["actor_id"])

    # ── work_sessions ──────────────────────────────────────────────────────────
    op.create_table(
        "work_sessions",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("employee_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("clock_in",         sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("clock_out",        sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("notes",            sa.Text(), nullable=True),
        sa.Column("created_at",       sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_work_sessions_employee_id", "work_sessions", ["employee_id"])


def downgrade():
    op.drop_table("work_sessions")
    op.drop_table("file_transfer_audit_logs")
    op.drop_index("ix_chat_messages_sender_id",       table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_files_uploader_id",     table_name="chat_files")
    op.drop_index("ix_chat_files_conversation_id", table_name="chat_files")
    op.drop_table("chat_files")
    sa.Enum(name="chat_message_type").drop(op.get_bind(), checkfirst=True)
    op.drop_table("chat_conversations")
    op.drop_table("employee_auth")
