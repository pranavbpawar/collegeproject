-- ==============================================================================
-- NEF Agent — Database Schema
-- Run: psql -U ztuser -d zerotrust -h localhost -f scripts/agent_schema.sql
-- ==============================================================================

-- Agent machine registry
CREATE TABLE IF NOT EXISTS agent_machines (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname     TEXT NOT NULL,
    username     TEXT,
    os           TEXT,
    os_version   TEXT,
    ip_address   TEXT,
    mac_address  TEXT,
    api_key      TEXT NOT NULL UNIQUE,
    status       TEXT NOT NULL DEFAULT 'offline',   -- online / offline
    first_seen   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_machines_status ON agent_machines(status);
CREATE INDEX IF NOT EXISTS idx_agent_machines_last_seen ON agent_machines(last_seen);

-- Agent events (all 8 data types stored as JSONB)
CREATE TABLE IF NOT EXISTS agent_events (
    id           BIGSERIAL PRIMARY KEY,
    agent_id     UUID NOT NULL REFERENCES agent_machines(id) ON DELETE CASCADE,
    event_type   TEXT NOT NULL,   -- sysinfo | processes | active_window | idle | usb_devices | screenshot | file_activity | websites
    payload      JSONB NOT NULL,
    collected_at TIMESTAMPTZ,
    received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_events_agent_id    ON agent_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_type        ON agent_events(event_type);
CREATE INDEX IF NOT EXISTS idx_agent_events_received_at ON agent_events(received_at DESC);

-- Screenshots stored separately (large payloads)
CREATE TABLE IF NOT EXISTS agent_screenshots (
    id           BIGSERIAL PRIMARY KEY,
    agent_id     UUID NOT NULL REFERENCES agent_machines(id) ON DELETE CASCADE,
    image_data   BYTEA NOT NULL,
    width        INTEGER,
    height       INTEGER,
    size_bytes   INTEGER,
    taken_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_screenshots_agent_id ON agent_screenshots(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_screenshots_taken_at ON agent_screenshots(taken_at DESC);
