-- Add 'cnki' as a valid source_type
ALTER TABLE journals DROP CONSTRAINT journals_source_type_check;
ALTER TABLE journals ADD CONSTRAINT journals_source_type_check
    CHECK (source_type IN ('rss', 'arxiv', 'crossref', 'cnki'));

-- Make doi nullable so CNKI articles (no DOI) don't conflict on UNIQUE(doi, journal_id)
ALTER TABLE articles ALTER COLUMN doi DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN doi SET DEFAULT NULL;

-- Add partial unique index for articles without DOI (e.g., CNKI) to prevent duplicates
CREATE UNIQUE INDEX idx_articles_dedup_url ON articles(journal_id, url)
    WHERE doi IS NULL AND url != '';
