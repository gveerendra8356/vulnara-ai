
-- Migration 003: add DeviceTokens table for FCM push notifications.
--
-- Neither the Task 1 schema nor the Task 2 API contract has any concept
-- of a registered push-notification device. Task 6 (mobile app) requires
-- the backend to push `alert.critical` events to FCM, which means it
-- needs somewhere to store each user's FCM registration token(s) and a
-- new endpoint for the app to register one after login. This migration
-- and the accompanying POST /devices/register route are new surface
-- area, not part of the original 26-endpoint contract -- flagging that
-- explicitly here and in the handoff notes so it doesn't look silently
-- assumed.
--
-- One user can have multiple tokens (phone + tablet, or a reinstalled
-- app issuing a new token) -- hence a separate table rather than a
-- single column on Users.

CREATE TABLE IF NOT EXISTS DeviceTokens (
    device_token_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    fcm_token          TEXT NOT NULL UNIQUE,
    platform           VARCHAR(10) NOT NULL CHECK (platform IN ('android', 'ios')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON DeviceTokens(user_id);

-- last_seen_at is bumped on every re-registration (e.g. app relaunch)
-- so a stale/uninstalled-app token can eventually be pruned by a future
-- cleanup job -- not built here, just leaving the column that makes it
-- possible later.