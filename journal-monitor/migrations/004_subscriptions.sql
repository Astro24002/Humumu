CREATE TABLE journal_subscriptions (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    journal_id  UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, journal_id)
);

CREATE TABLE author_tracking (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    author_name VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, author_name)
);

CREATE INDEX idx_author_tracking_name ON author_tracking(author_name);
CREATE INDEX idx_author_tracking_user ON author_tracking(user_id);

CREATE TABLE keyword_subscriptions (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keyword  VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, keyword)
);

CREATE INDEX idx_keyword_subscriptions_user ON keyword_subscriptions(user_id);
