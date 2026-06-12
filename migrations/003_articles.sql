CREATE TABLE articles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doi             VARCHAR(255) NOT NULL,
    title           TEXT NOT NULL,
    authors         TEXT[] NOT NULL DEFAULT '{}',
    abstract        TEXT NOT NULL DEFAULT '',
    journal_id      UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    publish_date    DATE,
    url             TEXT NOT NULL DEFAULT '',
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(doi, journal_id)
);

CREATE INDEX idx_articles_doi ON articles(doi);
CREATE INDEX idx_articles_journal ON articles(journal_id, publish_date DESC);
CREATE INDEX idx_articles_authors ON articles USING GIN(authors);
