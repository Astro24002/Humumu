CREATE TABLE IF NOT EXISTS cas_category_years (
    year INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS cas_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    year INTEGER NOT NULL REFERENCES cas_category_years(year) ON DELETE CASCADE,
    major VARCHAR(64) NOT NULL,
    minor VARCHAR(128) NOT NULL,
    zone SMALLINT NOT NULL CHECK (zone BETWEEN 1 AND 4),
    is_top BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (year, major, minor, zone, is_top)
);

CREATE TABLE IF NOT EXISTS journal_cas_categories (
    journal_id UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES cas_categories(id) ON DELETE CASCADE,
    PRIMARY KEY (journal_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_cas_categories_year_major
    ON cas_categories (year, major);
CREATE INDEX IF NOT EXISTS idx_journal_cas_categories_category
    ON journal_cas_categories (category_id);
