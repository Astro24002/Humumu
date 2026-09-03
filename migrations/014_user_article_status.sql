CREATE TABLE IF NOT EXISTS user_article_status (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    is_read BOOLEAN NOT NULL DEFAULT false,
    is_starred BOOLEAN NOT NULL DEFAULT false,
    is_later BOOLEAN NOT NULL DEFAULT false,
    original_clicked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, article_id)
);

CREATE INDEX IF NOT EXISTS idx_user_article_status_user_starred
    ON user_article_status (user_id) WHERE is_starred = true;
CREATE INDEX IF NOT EXISTS idx_user_article_status_user_later
    ON user_article_status (user_id) WHERE is_later = true;
