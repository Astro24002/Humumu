-- Article guid + multi-key partial unique indexes for DB-first dedup.
ALTER TABLE articles ADD COLUMN IF NOT EXISTS guid TEXT;

-- Old UNIQUE(doi, journal_id) from 003 conflicts with nullable empty DOI rows.
ALTER TABLE articles DROP CONSTRAINT IF EXISTS articles_doi_journal_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_journal_doi
    ON articles (journal_id, doi)
    WHERE doi IS NOT NULL AND doi <> '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_journal_guid
    ON articles (journal_id, guid)
    WHERE guid IS NOT NULL AND guid <> '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_journal_url
    ON articles (journal_id, url)
    WHERE url IS NOT NULL AND url <> '';
