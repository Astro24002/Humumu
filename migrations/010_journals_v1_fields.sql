ALTER TABLE journals DROP CONSTRAINT IF EXISTS journals_source_type_check;
ALTER TABLE journals ADD CONSTRAINT journals_source_type_check
    CHECK (source_type IN ('rss', 'atom', 'arxiv', 'crossref', 'pubmed', 'cnki'));

ALTER TABLE journals ADD COLUMN IF NOT EXISTS content_type VARCHAR(20) NOT NULL DEFAULT 'journal';
ALTER TABLE journals ADD COLUMN IF NOT EXISTS directory_status VARCHAR(20) NOT NULL DEFAULT 'public';
ALTER TABLE journals ADD COLUMN IF NOT EXISTS homepage_url TEXT NOT NULL DEFAULT '';
ALTER TABLE journals ADD COLUMN IF NOT EXISTS normalized_source_url TEXT;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS etag TEXT;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS last_modified TEXT;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS last_fetched_at TIMESTAMPTZ;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS last_success_at TIMESTAMPTZ;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS consecutive_failures INTEGER NOT NULL DEFAULT 0;
ALTER TABLE journals ADD COLUMN IF NOT EXISTS last_error TEXT;

ALTER TABLE journals DROP CONSTRAINT IF EXISTS journals_content_type_check;
ALTER TABLE journals ADD CONSTRAINT journals_content_type_check
    CHECK (content_type IN ('journal', 'preprint'));

ALTER TABLE journals DROP CONSTRAINT IF EXISTS journals_directory_status_check;
ALTER TABLE journals ADD CONSTRAINT journals_directory_status_check
    CHECK (directory_status IN ('private', 'pending_review', 'public', 'rejected', 'hidden'));

CREATE INDEX IF NOT EXISTS idx_journals_directory_status ON journals(directory_status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_journals_normalized_source_url
    ON journals (normalized_source_url)
    WHERE normalized_source_url IS NOT NULL;
