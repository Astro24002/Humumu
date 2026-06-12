CREATE TABLE journals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(255) UNIQUE NOT NULL,
    source_type     VARCHAR(20) NOT NULL CHECK (source_type IN ('rss', 'arxiv', 'crossref')),
    source_url      TEXT NOT NULL,
    fetch_interval  INTERVAL NOT NULL DEFAULT '30 minutes',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_journals_slug ON journals(slug);
CREATE INDEX idx_journals_active ON journals(is_active) WHERE is_active = true;
