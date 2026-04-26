-- ============================================================
-- TBAPS Full Database Migration
-- Paste this entire file into Supabase SQL Editor and click RUN
-- ============================================================

-- ── MIGRATION 1: Initial Core Schema ─────────────────────────

-- admin_users
CREATE TABLE IF NOT EXISTS admin_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_admin_users_email ON admin_users(email);

-- agent_machines
CREATE TABLE IF NOT EXISTS agent_machines (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname    VARCHAR(255) NOT NULL,
    username    VARCHAR(255),
    os          VARCHAR(64),
    os_version  VARCHAR(128),
    ip_address  VARCHAR(64),
    mac_address VARCHAR(64),
    api_key     VARCHAR(255) NOT NULL UNIQUE,
    status      VARCHAR(32) NOT NULL DEFAULT 'online',
    first_seen  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_agent_machines_status    ON agent_machines(status);
CREATE INDEX IF NOT EXISTS ix_agent_machines_last_seen ON agent_machines(last_seen);

-- agent_events
CREATE TABLE IF NOT EXISTS agent_events (
    id           BIGSERIAL PRIMARY KEY,
    agent_id     UUID NOT NULL REFERENCES agent_machines(id) ON DELETE CASCADE,
    event_type   VARCHAR(64) NOT NULL,
    payload      JSONB NOT NULL,
    collected_at TIMESTAMPTZ,
    received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_agent_events_agent_id    ON agent_events(agent_id);
CREATE INDEX IF NOT EXISTS ix_agent_events_event_type  ON agent_events(event_type);
CREATE INDEX IF NOT EXISTS ix_agent_events_received_at ON agent_events(received_at);

-- agent_screenshots
CREATE TABLE IF NOT EXISTS agent_screenshots (
    id          BIGSERIAL PRIMARY KEY,
    agent_id    UUID NOT NULL REFERENCES agent_machines(id) ON DELETE CASCADE,
    image_data  BYTEA NOT NULL,
    width       INTEGER,
    height      INTEGER,
    size_bytes  INTEGER,
    taken_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_agent_screenshots_agent_id ON agent_screenshots(agent_id);
CREATE INDEX IF NOT EXISTS ix_agent_screenshots_taken_at ON agent_screenshots(taken_at);

-- ── MIGRATION 2: Employees, Chat, File Sharing, Work Sessions ─

-- departments
CREATE TABLE IF NOT EXISTS departments (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- users (managers, HR, admins)
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255),
    full_name       VARCHAR(255),
    role            VARCHAR(50) NOT NULL DEFAULT 'manager',
    department_id   UUID REFERENCES departments(id),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_role  ON users(role);

-- employees
CREATE TABLE IF NOT EXISTS employees (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    full_name     VARCHAR(255) NOT NULL,
    department_id UUID REFERENCES departments(id),
    manager_id    UUID REFERENCES users(id),
    created_by    UUID REFERENCES users(id),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    onboarded_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_employees_email         ON employees(email);
CREATE INDEX IF NOT EXISTS ix_employees_department_id ON employees(department_id);
CREATE INDEX IF NOT EXISTS ix_employees_manager_id    ON employees(manager_id);

-- employee_auth
CREATE TABLE IF NOT EXISTS employee_auth (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id   UUID NOT NULL UNIQUE REFERENCES employees(id),
    password_hash TEXT NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_employee_auth_employee_id ON employee_auth(employee_id);

-- onboarding_audit_logs
CREATE TABLE IF NOT EXISTS onboarding_audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID REFERENCES employees(id),
    action      VARCHAR(100) NOT NULL,
    actor_id    UUID,
    actor_role  VARCHAR(50),
    detail      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_onboarding_audit_employee_id ON onboarding_audit_logs(employee_id);

-- chat_conversations
CREATE TABLE IF NOT EXISTS chat_conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id),
    staff_user_id   UUID NOT NULL,
    staff_role      VARCHAR(50) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_employee_id   ON chat_conversations(employee_id);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_staff_user_id ON chat_conversations(staff_user_id);

-- chat_message_type enum
DO $$ BEGIN
    CREATE TYPE chat_message_type AS ENUM ('text', 'file');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- chat_files
CREATE TABLE IF NOT EXISTS chat_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id),
    uploader_id     UUID NOT NULL,
    uploader_type   VARCHAR(20) NOT NULL,
    original_name   VARCHAR(255) NOT NULL,
    mime_type       VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    storage_path    TEXT NOT NULL,
    checksum_sha256 VARCHAR(64),
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_chat_files_conversation_id ON chat_files(conversation_id);
CREATE INDEX IF NOT EXISTS ix_chat_files_uploader_id     ON chat_files(uploader_id);

-- chat_messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id),
    sender_id       UUID NOT NULL,
    sender_type     VARCHAR(20) NOT NULL,
    message_type    chat_message_type NOT NULL DEFAULT 'text',
    content         TEXT,
    file_id         UUID REFERENCES chat_files(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_read         BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_sender_id       ON chat_messages(sender_id);

-- file_transfer_audit_logs
CREATE TABLE IF NOT EXISTS file_transfer_audit_logs (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id    UUID NOT NULL,
    actor_id   UUID NOT NULL,
    actor_type VARCHAR(20) NOT NULL,
    action     VARCHAR(20) NOT NULL,
    file_name  VARCHAR(255) NOT NULL,
    file_size  BIGINT,
    ip_address VARCHAR(50),
    detail     TEXT,
    timestamp  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ftaudit_file_id  ON file_transfer_audit_logs(file_id);
CREATE INDEX IF NOT EXISTS ix_ftaudit_actor_id ON file_transfer_audit_logs(actor_id);

-- work_sessions
CREATE TABLE IF NOT EXISTS work_sessions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id      UUID NOT NULL REFERENCES employees(id),
    clock_in         TIMESTAMPTZ NOT NULL,
    clock_out        TIMESTAMPTZ,
    duration_minutes INTEGER,
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_work_sessions_employee_id ON work_sessions(employee_id);

-- ── MIGRATION 3: KBT Token Columns ───────────────────────────

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS kbt_token_hash       TEXT        DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS kbt_token_expires_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS kbt_generated_at     TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_employees_kbt_token_hash
    ON employees(kbt_token_hash)
    WHERE kbt_token_hash IS NOT NULL;

-- ── MIGRATION 4: Activation Code System ──────────────────────

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS activation_code_hash       TEXT        DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS activation_code_expires_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS activation_status          TEXT        NOT NULL DEFAULT 'pending_activation',
    ADD COLUMN IF NOT EXISTS activated_at               TIMESTAMPTZ DEFAULT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'employees_activation_status_check'
    ) THEN
        ALTER TABLE employees
            ADD CONSTRAINT employees_activation_status_check
            CHECK (activation_status IN ('pending_activation', 'activated'));
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_employees_activation_status
    ON employees(activation_status)
    WHERE deleted_at IS NULL;

-- ── Alembic version tracking ──────────────────────────────────
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version(version_num)
VALUES ('2024_chat_fileshare_v1')
ON CONFLICT DO NOTHING;

-- ============================================================
-- Migration complete! All TBAPS tables created successfully.
-- ============================================================
