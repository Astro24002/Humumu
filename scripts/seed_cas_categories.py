"""Idempotent seed of CAS category facets from data/cas_categories_seed.json.

Inserts cas_category_years + cas_categories; skips rows that already match the
unique (year, major, minor, zone, is_top) key. Does not attach journals.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import psycopg2

from app.config import get_settings

DEFAULT_SEED = Path(__file__).resolve().parents[1] / "data" / "cas_categories_seed.json"


def load_seed(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("seed file must be a JSON array")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"seed[{i}] must be an object")
        year = item.get("year")
        if not isinstance(year, int) or year < 2000 or year > 2100:
            raise ValueError(f"seed[{i}].year must be an int in 2000–2100")
        major = str(item.get("major") or "").strip()
        minor = str(item.get("minor") or "").strip()
        if not major or not minor:
            raise ValueError(f"seed[{i}].major and minor are required")
        zone = item.get("zone")
        if not isinstance(zone, int) or zone < 1 or zone > 4:
            raise ValueError(f"seed[{i}].zone must be an int 1–4")
        is_top = bool(item.get("is_top", False))
        out.append(
            {
                "year": year,
                "major": major,
                "minor": minor,
                "zone": zone,
                "is_top": is_top,
            }
        )
    return out


def upsert_categories(cur: Any, rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Ensure years + categories. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0
    years = sorted({r["year"] for r in rows}, reverse=True)
    for year in years:
        cur.execute(
            """
            INSERT INTO cas_category_years (year)
            VALUES (%s)
            ON CONFLICT (year) DO NOTHING
            """,
            (year,),
        )
    for row in rows:
        cur.execute(
            """
            INSERT INTO cas_categories (year, major, minor, zone, is_top)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (year, major, minor, zone, is_top) DO NOTHING
            RETURNING id
            """,
            (row["year"], row["major"], row["minor"], row["zone"], row["is_top"]),
        )
        got = cur.fetchone()
        if got:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    seed_path = DEFAULT_SEED
    if args:
        seed_path = Path(args[0])

    if not seed_path.is_file():
        print(f"seed file not found: {seed_path}", file=sys.stderr)
        return 1

    try:
        rows = load_seed(seed_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"seed load failed: {exc}", file=sys.stderr)
        return 1

    settings = get_settings()
    conn = None
    try:
        conn = psycopg2.connect(settings.sync_dsn())
        conn.autocommit = False
        with conn.cursor() as cur:
            inserted, skipped = upsert_categories(cur, rows)
        conn.commit()
        print(
            f"seed cas categories: {len(rows)} rows "
            f"({inserted} inserted, {skipped} already present) from {seed_path}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        if conn is not None:
            conn.rollback()
        print(f"seed cas categories failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
