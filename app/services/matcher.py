"""Pure-ish article matcher: journal subscribers ∪ authors ∪ keywords.

Realtime path ignores ``push_frequency``. Channel is wechat if user has
wechat_openid, else email.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence
from uuid import UUID


@dataclass(frozen=True)
class MatchResult:
    user_id: str
    article_id: str
    channel: str = "email"


def match_authors(
    *,
    article_id: str,
    article_authors: Sequence[str],
    tracked: Iterable[tuple[str, str]],  # (user_id, author_name)
) -> list[MatchResult]:
    """Casefold equality on trimmed author names."""
    if not article_authors:
        return []
    article_set = {a.strip().casefold() for a in article_authors if a and a.strip()}
    if not article_set:
        return []

    results: list[MatchResult] = []
    for user_id, author_name in tracked:
        name = (author_name or "").strip().casefold()
        if name and name in article_set:
            results.append(MatchResult(user_id=str(user_id), article_id=str(article_id)))
    return results


def match_keywords(
    *,
    article_id: str,
    title: str,
    abstract: str,
    keywords: Iterable[tuple[str, str]],  # (user_id, keyword)
) -> list[MatchResult]:
    """Keyword substring match (case-insensitive) in title or abstract."""
    hay_title = (title or "").casefold()
    hay_abs = (abstract or "").casefold()
    if not hay_title and not hay_abs:
        return []

    results: list[MatchResult] = []
    for user_id, keyword in keywords:
        kw = (keyword or "").strip().casefold()
        if not kw:
            continue
        if kw in hay_title or kw in hay_abs:
            results.append(MatchResult(user_id=str(user_id), article_id=str(article_id)))
    return results


def match_journal_subscribers(
    *,
    article_id: str,
    subscriber_ids: Iterable[str | UUID],
) -> list[MatchResult]:
    return [
        MatchResult(user_id=str(uid), article_id=str(article_id))
        for uid in subscriber_ids
    ]


def dedupe_by_user(results: Sequence[MatchResult]) -> list[MatchResult]:
    """Keep first match per user_id (single article context)."""
    seen: set[str] = set()
    out: list[MatchResult] = []
    for r in results:
        if r.user_id in seen:
            continue
        seen.add(r.user_id)
        out.append(r)
    return out


def resolve_channel(wechat_openid: str | None) -> str:
    """wechat if openid present, else email. Ignores push_frequency."""
    if wechat_openid and str(wechat_openid).strip():
        return "wechat"
    return "email"


def apply_channels(
    results: Sequence[MatchResult],
    user_openid: dict[str, str | None],
) -> list[MatchResult]:
    """Attach channel from user openid map."""
    out: list[MatchResult] = []
    for r in results:
        ch = resolve_channel(user_openid.get(r.user_id))
        out.append(MatchResult(user_id=r.user_id, article_id=r.article_id, channel=ch))
    return out


def match_article(
    *,
    article_id: str,
    journal_subscriber_ids: Sequence[str | UUID],
    article_authors: Sequence[str],
    title: str,
    abstract: str,
    tracked_authors: Sequence[tuple[str, str]],
    keywords: Sequence[tuple[str, str]],
    user_openid: dict[str, str | None],
) -> list[MatchResult]:
    """
    Full match: journal ∪ author ∪ keyword, dedupe by user, resolve channel.

    Does **not** filter by push_frequency (realtime path notifies all matches).
    """
    results: list[MatchResult] = []
    results.extend(
        match_journal_subscribers(
            article_id=article_id,
            subscriber_ids=journal_subscriber_ids,
        )
    )
    results.extend(
        match_authors(
            article_id=article_id,
            article_authors=article_authors,
            tracked=tracked_authors,
        )
    )
    results.extend(
        match_keywords(
            article_id=article_id,
            title=title,
            abstract=abstract,
            keywords=keywords,
        )
    )
    results = dedupe_by_user(results)
    return apply_channels(results, user_openid)
