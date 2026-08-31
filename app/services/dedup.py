"""Article dedup via Redis SET NX EX (7-day TTL).

Return convention for ``is_duplicate_and_mark``:
  True  → key was set (article is NEW; process it)
  False → key already existed (duplicate; skip)

When redis client ``r`` is None, always returns True (treat as new).
"""

from __future__ import annotations

from typing import Any

DEDUP_TTL_SECONDS = 604800  # 7 days


def dedup_key(journal_id: str, doi: str | None, url: str) -> str:
    """Build Redis key: doi preferred, else url fallback."""
    doi_s = (doi or "").strip()
    if doi_s:
        return f"dedup:{journal_id}:{doi_s}"
    return f"dedup:{journal_id}:url:{url}"


async def is_duplicate_and_mark(
    r: Any,
    journal_id: str,
    doi: str | None,
    url: str,
) -> bool:
    """
    Atomically mark article as seen.

    Returns:
        True if set succeeded (new article), False if key already existed
        (duplicate). If ``r`` is None, returns True (no-op dedup).
    """
    if r is None:
        return True

    doi_s = (doi or "").strip()
    url_s = (url or "").strip()
    if not doi_s and not url_s:
        # Nothing to key on — treat as new (caller may still skip empty titles)
        return True

    key = dedup_key(journal_id, doi_s or None, url_s)
    # SET key value NX EX ttl → True if set, None/False if existed
    was_set = await r.set(key, "1", nx=True, ex=DEDUP_TTL_SECONDS)
    return bool(was_set)
