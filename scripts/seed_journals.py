"""Idempotent seed of built-in journals from data/journals_seed.json.

Upserts by slug (preferred) or source_url. Does not deactivate journals that
were removed from the seed file — admin-managed rows stay intact.

Sets content_type, directory_status=public, homepage_url, and normalized_source_url.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import psycopg2

from app.config import get_settings
from app.services.feed_url import normalize_feed_url

DEFAULT_SEED = Path(__file__).resolve().parents[1] / "data" / "journals_seed.json"

REQUIRED_FIELDS = ("name", "slug", "source_type", "source_url")
_VALID_CONTENT_TYPES = frozenset({"journal", "preprint"})

_PREPRINT_HOST_MARKERS = (
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
)


def _infer_content_type(source_url: str, explicit: str | None) -> str:
    if explicit:
        ct = explicit.strip().lower()
        if ct in _VALID_CONTENT_TYPES:
            return ct
    host = (source_url or "").lower()
    if any(m in host for m in _PREPRINT_HOST_MARKERS):
        return "preprint"
    return "journal"


def load_seed(path: Path) -> list[dict[str, Any]]:
    """Load and lightly validate seed JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("seed file must be a JSON array")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"seed[{i}] must be an object")
        for key in REQUIRED_FIELDS:
            val = item.get(key)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"seed[{i}].{key} must be a non-empty string")
        minutes = item.get("fetch_interval_minutes", 60)
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError(f"seed[{i}].fetch_interval_minutes must be a positive int")
        source_url = item["source_url"].strip()
        content_type = _infer_content_type(source_url, item.get("content_type"))
        normalized = normalize_feed_url(source_url) or source_url
        out.append(
            {
                "name": item["name"].strip(),
                "slug": item["slug"].strip().lower(),
                "source_type": item["source_type"].strip().lower(),
                "source_url": source_url,
                "description": str(item.get("description") or "").strip(),
                "fetch_interval_minutes": minutes,
                "is_active": bool(item.get("is_active", True)),
                "content_type": content_type,
                "directory_status": "public",
                "homepage_url": str(item.get("homepage_url") or "").strip(),
                "normalized_source_url": normalized,
            }
        )
    return out


def upsert_journals(cur: Any, rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Insert or update journals. Returns (inserted, updated)."""
    inserted = 0
    updated = 0
    for row in rows:
        cur.execute(
            """
            SELECT id FROM journals
            WHERE slug = %s
               OR source_url = %s
               OR normalized_source_url = %s
            LIMIT 1
            """,
            (row["slug"], row["source_url"], row["normalized_source_url"]),
        )
        existing = cur.fetchone()
        interval = f"{row['fetch_interval_minutes']} minutes"
        if existing:
            cur.execute(
                """
                UPDATE journals
                SET name = %s,
                    slug = %s,
                    source_type = %s,
                    source_url = %s,
                    description = %s,
                    fetch_interval = %s::interval,
                    is_active = %s,
                    content_type = %s,
                    directory_status = %s,
                    homepage_url = %s,
                    normalized_source_url = %s
                WHERE id = %s
                """,
                (
                    row["name"],
                    row["slug"],
                    row["source_type"],
                    row["source_url"],
                    row["description"],
                    interval,
                    row["is_active"],
                    row["content_type"],
                    row["directory_status"],
                    row["homepage_url"],
                    row["normalized_source_url"],
                    existing[0],
                ),
            )
            updated += 1
        else:
            cur.execute(
                """
                INSERT INTO journals (
                    name, slug, source_type, source_url, description,
                    fetch_interval, is_active,
                    content_type, directory_status, homepage_url, normalized_source_url
                ) VALUES (
                    %s, %s, %s, %s, %s, %s::interval, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    row["name"],
                    row["slug"],
                    row["source_type"],
                    row["source_url"],
                    row["description"],
                    interval,
                    row["is_active"],
                    row["content_type"],
                    row["directory_status"],
                    row["homepage_url"],
                    row["normalized_source_url"],
                ),
            )
            inserted += 1
    return inserted, updated


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
            inserted, updated = upsert_journals(cur, rows)
        conn.commit()
        print(
            f"seed journals: {len(rows)} rows "
            f"({inserted} inserted, {updated} updated) from {seed_path}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        if conn is not None:
            conn.rollback()
        print(f"seed journals failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
