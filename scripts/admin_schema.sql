-- ============================================================================
-- TBAPS Admin Users Schema
-- Run this ONCE after init_schema.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin_users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username    VARCHAR(100) NOT NULL UNIQUE,
    email       VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login  TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username);
CREATE INDEX IF NOT EXISTS idx_admin_users_email    ON admin_users(email);

-- Default admin account: username=admin  password=Admin@1234
-- Change the password immediately after first login!
-- To generate a new hash:  python3 -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('YourPassword'))"
INSERT INTO admin_users (username, email, password_hash)
VALUES (
    'admin',
    'admin@tbaps.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2NJv.Hmr2q'  -- Admin@1234
) ON CONFLICT (username) DO NOTHING;
