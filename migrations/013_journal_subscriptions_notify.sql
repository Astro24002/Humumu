ALTER TABLE journal_subscriptions
    ADD COLUMN IF NOT EXISTS push_frequency VARCHAR(20) NOT NULL DEFAULT 'default';
ALTER TABLE journal_subscriptions
    ADD COLUMN IF NOT EXISTS email_enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE journal_subscriptions
    ADD COLUMN IF NOT EXISTS wechat_enabled BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE journal_subscriptions DROP CONSTRAINT IF EXISTS journal_subscriptions_push_frequency_check;
ALTER TABLE journal_subscriptions ADD CONSTRAINT journal_subscriptions_push_frequency_check
    CHECK (push_frequency IN ('default', 'realtime', 'daily'));

-- New users default to daily summary (existing rows unchanged).
ALTER TABLE users ALTER COLUMN push_frequency SET DEFAULT 'daily';
