-- Migration 002: extend Threat_Logs.attack_type to include command injection.
--
-- Task 1's original schema only anticipated SQLi/XSS active testing
-- ("Active testing (opt-in, rate-limited) -- controlled SQLi/XSS-style
-- payloads"). Task 5 explicitly asks for command injection payloads too,
-- so the CHECK constraint needs to widen accordingly. Run this against
-- your existing Neon database before deploying the active testing module.

ALTER TABLE Threat_Logs
    DROP CONSTRAINT IF EXISTS threat_logs_attack_type_check;

ALTER TABLE Threat_Logs
    ADD CONSTRAINT threat_logs_attack_type_check
    CHECK (attack_type IN ('SQLI', 'XSS', 'CMDI'));

-- NOTE: the exact auto-generated constraint name above
-- (threat_logs_attack_type_check) is Postgres's default naming
-- convention for an unnamed CHECK constraint on this column
-- (table_column_check). Verify the actual name in your database first:
--
--   SELECT conname FROM pg_constraint
--   WHERE conrelid = 'threat_logs'::regclass AND contype = 'c';
--
-- and adjust the DROP CONSTRAINT line if it differs (e.g. if you named
-- it explicitly when running the original Task 1 CREATE TABLE).
