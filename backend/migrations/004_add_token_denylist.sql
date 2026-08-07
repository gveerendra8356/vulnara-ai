-- Migration to add TokenDenylist table
-- Assuming PostgreSQL dialect

CREATE TABLE IF NOT EXISTS token_denylist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token VARCHAR(512) UNIQUE NOT NULL, -- This will store a SHA-256 hash of the token
    blacklisted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_token_denylist_token ON token_denylist(token);
