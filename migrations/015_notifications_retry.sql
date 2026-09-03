ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ;
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS match_reasons TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_notifications_pending_dispatch
    ON notifications (status, next_attempt_at)
    WHERE status = 'pending';
