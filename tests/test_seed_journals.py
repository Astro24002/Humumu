import json
from pathlib import Path

import pytest

from scripts.seed_journals import load_seed, upsert_journals

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "journals_seed.json"


def test_repo_seed_file_loads_and_has_unique_slugs():
    rows = load_seed(SEED)
    assert len(rows) >= 20
    slugs = [r["slug"] for r in rows]
    urls = [r["source_url"] for r in rows]
    assert len(slugs) == len(set(slugs))
    assert len(urls) == len(set(urls))
    preprint_count = 0
    for r in rows:
        assert r["source_type"] in {"rss", "arxiv", "crossref", "cnki", "atom"}
        assert r["source_url"].startswith("http")
        assert r["fetch_interval_minutes"] > 0
        assert r["content_type"] in {"journal", "preprint"}
        assert r["directory_status"] == "public"
        assert r["normalized_source_url"]
        if "arxiv.org" in r["source_url"] or "biorxiv" in r["source_url"] or "medrxiv" in r["source_url"]:
            assert r["content_type"] == "preprint"
            preprint_count += 1
    assert preprint_count >= 5


def test_load_seed_rejects_missing_fields(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([{"name": "X"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="slug"):
        load_seed(p)


def test_upsert_insert_then_update():
    calls: list[tuple] = []

    class FakeCursor:
        def __init__(self) -> None:
            self._found = False

        def execute(self, sql: str, params=None) -> None:  # noqa: ANN001
            calls.append((sql.strip().split()[0].upper(), params))
            self._last_sql = sql

        def fetchone(self):
            if "SELECT" in self._last_sql.upper():
                if self._found:
                    return ("existing-id",)
                self._found = True
                return None
            return None

    cur = FakeCursor()
    row = {
        "name": "arXiv cs.AI",
        "slug": "arxiv-cs-ai",
        "source_type": "rss",
        "source_url": "https://rss.arxiv.org/rss/cs.AI",
        "description": "AI",
        "fetch_interval_minutes": 60,
        "is_active": True,
        "content_type": "preprint",
        "directory_status": "public",
        "homepage_url": "",
        "normalized_source_url": "https://rss.arxiv.org/rss/cs.AI",
    }
    inserted, updated = upsert_journals(cur, [row])
    assert (inserted, updated) == (1, 0)
    inserted2, updated2 = upsert_journals(cur, [row])
    assert (inserted2, updated2) == (0, 1)
    verbs = [c[0] for c in calls]
    assert verbs.count("SELECT") == 2
    assert verbs.count("INSERT") == 1
    assert verbs.count("UPDATE") == 1
    # INSERT includes content_type / normalized_source_url
    insert_params = [c[1] for c in calls if c[0] == "INSERT"][0]
    assert "preprint" in insert_params
