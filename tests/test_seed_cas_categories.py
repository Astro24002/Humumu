import json
from pathlib import Path

import pytest

from scripts.seed_cas_categories import load_seed, upsert_categories

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "cas_categories_seed.json"


def test_repo_cas_seed_file_loads_and_unique_keys():
    rows = load_seed(SEED)
    assert len(rows) >= 10
    keys = [(r["year"], r["major"], r["minor"], r["zone"], r["is_top"]) for r in rows]
    assert len(keys) == len(set(keys))
    for r in rows:
        assert 2000 <= r["year"] <= 2100
        assert r["major"]
        assert r["minor"]
        assert 1 <= r["zone"] <= 4
        assert isinstance(r["is_top"], bool)


def test_load_cas_seed_rejects_bad_zone(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps([{"year": 2025, "major": "数学", "minor": "数学", "zone": 9}]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="zone"):
        load_seed(p)


def test_upsert_cas_insert_then_skip():
    class FakeCursor:
        def __init__(self) -> None:
            self._seen: set[tuple] = set()
            self._last_sql = ""
            self._last_params = None

        def execute(self, sql: str, params=None) -> None:  # noqa: ANN001
            self._last_sql = sql
            self._last_params = params

        def fetchone(self):
            if "RETURNING" not in self._last_sql.upper():
                return None
            key = tuple(self._last_params)
            if key in self._seen:
                return None
            self._seen.add(key)
            return ("new-id",)

    cur = FakeCursor()
    row = {
        "year": 2025,
        "major": "数学",
        "minor": "数学",
        "zone": 1,
        "is_top": True,
    }
    inserted, skipped = upsert_categories(cur, [row])
    assert (inserted, skipped) == (1, 0)
    inserted2, skipped2 = upsert_categories(cur, [row])
    assert (inserted2, skipped2) == (0, 1)
