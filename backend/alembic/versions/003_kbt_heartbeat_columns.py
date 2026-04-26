"""
KBT Heartbeat Columns Migration
Adds kbt_last_heartbeat_at and kbt_device_id to the employees table
to track KBT client connectivity from the Employee Web Portal.

Revision ID: 003_kbt_heartbeat_columns
Revises: 2024_chat_fileshare_v1
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision      = "003_kbt_heartbeat_columns"
down_revision = "2024_chat_fileshare_v1"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # Add heartbeat tracking columns to employees table
    # Use IF NOT EXISTS equivalent via try/except at column level
    # (PostgreSQL 9.6+ supports ADD COLUMN IF NOT EXISTS)
    op.execute("""
        ALTER TABLE employees
            ADD COLUMN IF NOT EXISTS kbt_last_heartbeat_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS kbt_device_id         TEXT
    """)

    # Index on heartbeat timestamp for efficient "online employees" queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_employees_kbt_last_heartbeat_at
            ON employees (kbt_last_heartbeat_at)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_employees_kbt_last_heartbeat_at")
    op.execute("""
        ALTER TABLE employees
            DROP COLUMN IF EXISTS kbt_last_heartbeat_at,
            DROP COLUMN IF EXISTS kbt_device_id
    """)
