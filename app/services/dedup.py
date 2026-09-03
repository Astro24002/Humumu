"""Article dedup via Redis SET NX EX (7-day TTL) with multi-key support.

Priority for primary key: DOI > guid > url.

Return convention for ``is_duplicate_and_mark``:
  True  → key was set (article is NEW; process it)
  False → key already existed (duplicate; skip)

When redis client ``r`` is None, always returns True (treat as new).
"""

from __future__ import annotations

from typing import Any

DEDUP_TTL_SECONDS = 604800  # 7 days


def _clean(value: str | None) -> str:
    return (value or "").strip()


def dedup_key(
    journal_id: str,
    doi: str | None,
    url: str,
    guid: str | None = None,
) -> str:
    """Build primary Redis key: doi preferred, else guid, else url fallback."""
    doi_s = _clean(doi)
    if doi_s:
        return f"dedup:{journal_id}:{doi_s}"
    guid_s = _clean(guid)
    if guid_s:
        return f"dedup:{journal_id}:guid:{guid_s}"
    return f"dedup:{journal_id}:url:{_clean(url)}"


def dedup_keys(
    journal_id: str,
    *,
    doi: str | None = None,
    guid: str | None = None,
    url: str | None = None,
) -> list[str]:
    """All applicable Redis keys for multi-key mark (DOI, guid, url)."""
    keys: list[str] = []
    doi_s = _clean(doi)
    guid_s = _clean(guid)
    url_s = _clean(url)
    if doi_s:
        keys.append(f"dedup:{journal_id}:{doi_s}")
    if guid_s:
        keys.append(f"dedup:{journal_id}:guid:{guid_s}")
    if url_s:
        keys.append(f"dedup:{journal_id}:url:{url_s}")
    return keys


async def is_duplicate_and_mark(
    r: Any,
    journal_id: str,
    doi: str | None,
    url: str,
    guid: str | None = None,
) -> bool:
    """
    Atomically mark article as seen under all applicable keys.

    Returns:
        True if primary key was newly set (new article),
        False if any key already existed (duplicate).
        If ``r`` is None, returns True (no-op dedup).
    """
    if r is None:
        return True

    keys = dedup_keys(journal_id, doi=doi, guid=guid, url=url)
    if not keys:
        return True

    for key in keys:
        try:
            if await r.exists(key):
                for k in keys:
                    try:
                        await r.set(k, "1", ex=DEDUP_TTL_SECONDS)
                    except Exception:
                        pass
                return False
        except Exception:
            pass

    primary = keys[0]
    was_set = await r.set(primary, "1", nx=True, ex=DEDUP_TTL_SECONDS)
    if not was_set:
        return False
    for k in keys[1:]:
        try:
            await r.set(k, "1", nx=True, ex=DEDUP_TTL_SECONDS)
        except Exception:
            pass
    return True
