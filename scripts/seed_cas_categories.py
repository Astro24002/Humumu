"""Idempotent seed of CAS category facets from data/cas_categories_seed.json.

Inserts cas_category_years + cas_categories; skips rows that already match the
unique (year, major, minor, zone, is_top) key.

Optional demo journal attachments (data/cas_journal_attach_seed.json) link seed
journals by slug to facet rows so plaza CAS filters return sample hits after
`make seed` + `make seed-cas`. Attachments are opt-in via --attach (or HUMUMU_SEED_CAS_ATTACH=1).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2

from app.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "data" / "cas_categories_seed.json"
DEFAULT_ATTACH = ROOT / "data" / "cas_journal_attach_seed.json"


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


def load_attach_seed(path: Path) -> list[dict[str, Any]]:
    """journal_slug + CAS facet tuple rows for demo attachments."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("attach seed must be a JSON array")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"attach[{i}] must be an object")
        slug = str(item.get("journal_slug") or "").strip()
        if not slug:
            raise ValueError(f"attach[{i}].journal_slug is required")
        year = item.get("year")
        if not isinstance(year, int) or year < 2000 or year > 2100:
            raise ValueError(f"attach[{i}].year must be an int in 2000–2100")
        major = str(item.get("major") or "").strip()
        minor = str(item.get("minor") or "").strip()
        if not major or not minor:
            raise ValueError(f"attach[{i}].major and minor are required")
        zone = item.get("zone")
        if not isinstance(zone, int) or zone < 1 or zone > 4:
            raise ValueError(f"attach[{i}].zone must be an int 1–4")
        is_top = bool(item.get("is_top", False))
        out.append(
            {
                "journal_slug": slug,
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


def attach_journals(cur: Any, rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Link journals by slug to CAS facets. Returns (linked, already, skipped_missing)."""
    linked = 0
    already = 0
    missing = 0
    for row in rows:
        cur.execute(
            "SELECT id FROM journals WHERE slug = %s LIMIT 1",
            (row["journal_slug"],),
        )
        j = cur.fetchone()
        if not j:
            missing += 1
            continue
        journal_id = j[0]
        cur.execute(
            """
            SELECT id FROM cas_categories
            WHERE year = %s AND major = %s AND minor = %s AND zone = %s AND is_top = %s
            LIMIT 1
            """,
            (row["year"], row["major"], row["minor"], row["zone"], row["is_top"]),
        )
        c = cur.fetchone()
        if not c:
            missing += 1
            continue
        category_id = c[0]
        cur.execute(
            """
            INSERT INTO journal_cas_categories (journal_id, category_id)
            VALUES (%s, %s)
            ON CONFLICT (journal_id, category_id) DO NOTHING
            RETURNING journal_id
            """,
            (journal_id, category_id),
        )
        got = cur.fetchone()
        if got:
            linked += 1
        else:
            already += 1
    return linked, already, missing


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    seed_path = DEFAULT_SEED
    attach_path = DEFAULT_ATTACH
    do_attach = os.environ.get("HUMUMU_SEED_CAS_ATTACH", "").strip() in {"1", "true", "yes"}
    positional: list[str] = []
    for a in args:
        if a in {"--attach", "-a"}:
            do_attach = True
        elif a in {"--no-attach"}:
            do_attach = False
        elif a.startswith("-"):
            print(f"unknown flag: {a}", file=sys.stderr)
            return 2
        else:
            positional.append(a)
    if positional:
        seed_path = Path(positional[0])
    if len(positional) > 1:
        attach_path = Path(positional[1])

    if not seed_path.is_file():
        print(f"seed file not found: {seed_path}", file=sys.stderr)
        return 1

    try:
        rows = load_seed(seed_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"seed load failed: {exc}", file=sys.stderr)
        return 1

    attach_rows: list[dict[str, Any]] = []
    if do_attach:
        if not attach_path.is_file():
            print(f"attach seed file not found: {attach_path}", file=sys.stderr)
            return 1
        try:
            attach_rows = load_attach_seed(attach_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"attach seed load failed: {exc}", file=sys.stderr)
            return 1

    settings = get_settings()
    conn = None
    try:
        conn = psycopg2.connect(settings.sync_dsn())
        conn.autocommit = False
        with conn.cursor() as cur:
            inserted, skipped = upsert_categories(cur, rows)
            link_msg = ""
            if attach_rows:
                linked, already, missing = attach_journals(cur, attach_rows)
                link_msg = (
                    f"; attach {len(attach_rows)} "
                    f"({linked} linked, {already} already, {missing} skipped)"
                )
        conn.commit()
        print(
            f"seed cas categories: {len(rows)} rows "
            f"({inserted} inserted, {skipped} already present) from {seed_path}"
            f"{link_msg}"
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
