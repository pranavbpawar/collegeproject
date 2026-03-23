"""
Initial TBAPS Schema Migration
Creates core tables: agent_machines, agent_events, agent_screenshots, admin_users.

Revision ID: 001
Revises: (initial)
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


# revision identifiers
revision   = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── admin_users ────────────────────────────────────────────────────────────
    op.create_table(
        "admin_users",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email",        sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active",    sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"])

    # ── agent_machines ─────────────────────────────────────────────────────────
    op.create_table(
        "agent_machines",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hostname",    sa.String(255), nullable=False),
        sa.Column("username",    sa.String(255), nullable=True),
        sa.Column("os",          sa.String(64),  nullable=True),
        sa.Column("os_version",  sa.String(128), nullable=True),
        sa.Column("ip_address",  sa.String(64),  nullable=True),
        sa.Column("mac_address", sa.String(64),  nullable=True),
        sa.Column("api_key",     sa.String(255), nullable=False, unique=True),
        sa.Column("status",      sa.String(32),  server_default="'online'", nullable=False),
        sa.Column("first_seen",  sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_seen",   sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_agent_machines_status",       "agent_machines", ["status"])
    op.create_index("ix_agent_machines_last_seen",    "agent_machines", ["last_seen"])

    # ── agent_events ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_events",
        sa.Column("id",           sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("agent_id",     UUID(as_uuid=True), sa.ForeignKey("agent_machines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type",   sa.String(64), nullable=False),
        sa.Column("payload",      JSONB(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at",  sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_agent_events_agent_id",    "agent_events", ["agent_id"])
    op.create_index("ix_agent_events_event_type",  "agent_events", ["event_type"])
    op.create_index("ix_agent_events_received_at", "agent_events", ["received_at"])

    # ── agent_screenshots ──────────────────────────────────────────────────────
    op.create_table(
        "agent_screenshots",
        sa.Column("id",          sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("agent_id",    UUID(as_uuid=True), sa.ForeignKey("agent_machines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_data",  sa.LargeBinary(), nullable=False),
        sa.Column("width",       sa.Integer(), nullable=True),
        sa.Column("height",      sa.Integer(), nullable=True),
        sa.Column("size_bytes",  sa.Integer(), nullable=True),
        sa.Column("taken_at",    sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_agent_screenshots_agent_id", "agent_screenshots", ["agent_id"])
    op.create_index("ix_agent_screenshots_taken_at", "agent_screenshots", ["taken_at"])


def downgrade() -> None:
    op.drop_table("agent_screenshots")
    op.drop_table("agent_events")
    op.drop_table("agent_machines")
    op.drop_table("admin_users")
