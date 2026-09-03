"""Pure-ish article matcher: journal subscribers ∪ authors ∪ keywords.

Channel is wechat if user has wechat_openid, else email.
MatchResult.reasons collects hit types (journal/author/keyword).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Sequence
from uuid import UUID


@dataclass(frozen=True)
class MatchResult:
    user_id: str
    article_id: str
    channel: str = "email"
    reasons: tuple[str, ...] = ()


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
            results.append(
                MatchResult(
                    user_id=str(user_id),
                    article_id=str(article_id),
                    reasons=("author",),
                )
            )
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
            results.append(
                MatchResult(
                    user_id=str(user_id),
                    article_id=str(article_id),
                    reasons=("keyword",),
                )
            )
    return results


def match_journal_subscribers(
    *,
    article_id: str,
    subscriber_ids: Iterable[str | UUID],
) -> list[MatchResult]:
    return [
        MatchResult(
            user_id=str(uid),
            article_id=str(article_id),
            reasons=("journal",),
        )
        for uid in subscriber_ids
    ]


def dedupe_by_user(results: Sequence[MatchResult]) -> list[MatchResult]:
    """Merge matches per user_id, unioning reasons (order preserved)."""
    order: list[str] = []
    by_user: dict[str, MatchResult] = {}
    for r in results:
        existing = by_user.get(r.user_id)
        if existing is None:
            order.append(r.user_id)
            # de-dupe reasons while preserving order
            seen: set[str] = set()
            reasons: list[str] = []
            for reason in r.reasons:
                if reason not in seen:
                    seen.add(reason)
                    reasons.append(reason)
            by_user[r.user_id] = replace(r, reasons=tuple(reasons))
            continue
        seen = set(existing.reasons)
        merged = list(existing.reasons)
        for reason in r.reasons:
            if reason not in seen:
                seen.add(reason)
                merged.append(reason)
        by_user[r.user_id] = replace(existing, reasons=tuple(merged))
    return [by_user[uid] for uid in order]


def resolve_channel(wechat_openid: str | None) -> str:
    """wechat if openid present, else email."""
    if wechat_openid and str(wechat_openid).strip():
        return "wechat"
    return "email"


def apply_channels(
    results: Sequence[MatchResult],
    user_openid: dict[str, str | None],
) -> list[MatchResult]:
    """Attach channel from user openid map (preserves reasons)."""
    out: list[MatchResult] = []
    for r in results:
        ch = resolve_channel(user_openid.get(r.user_id))
        out.append(
            MatchResult(
                user_id=r.user_id,
                article_id=r.article_id,
                channel=ch,
                reasons=r.reasons,
            )
        )
    return out


def expand_channels(
    results: Sequence[MatchResult],
    *,
    user_openid: dict[str, str | None],
    user_email: dict[str, str] | None = None,
    channel_prefs: dict[str, tuple[bool, bool]] | None = None,
) -> list[MatchResult]:
    """
    Expand one match into per-enabled-channel rows.

    channel_prefs maps user_id -> (email_enabled, wechat_enabled).
    Default both enabled when prefs missing.
    Only emit wechat if openid present; email if email present (or unknown).
    """
    user_email = user_email or {}
    channel_prefs = channel_prefs or {}
    out: list[MatchResult] = []
    for r in results:
        email_on, wechat_on = channel_prefs.get(r.user_id, (True, True))
        openid = user_openid.get(r.user_id)
        email = (user_email.get(r.user_id) or "").strip()
        if email_on and (email or r.user_id not in user_email):
            # If email map doesn't know user, still allow email channel
            if email or r.user_id not in user_email:
                out.append(
                    MatchResult(
                        user_id=r.user_id,
                        article_id=r.article_id,
                        channel="email",
                        reasons=r.reasons,
                    )
                )
        if wechat_on and openid and str(openid).strip():
            out.append(
                MatchResult(
                    user_id=r.user_id,
                    article_id=r.article_id,
                    channel="wechat",
                    reasons=r.reasons,
                )
            )
        # Fallback: if nothing emitted, keep single resolved channel
        if not any(x.user_id == r.user_id and x.article_id == r.article_id for x in out[-2:]):
            if not any(
                x.user_id == r.user_id and x.article_id == r.article_id for x in out
            ):
                out.append(
                    MatchResult(
                        user_id=r.user_id,
                        article_id=r.article_id,
                        channel=resolve_channel(openid),
                        reasons=r.reasons,
                    )
                )
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
    Full match: journal ∪ author ∪ keyword, merge reasons by user, resolve channel.

    Does **not** filter by push_frequency (caller may gate realtime separately).
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


def effective_push_frequency(sub_freq: str | None, user_freq: str | None) -> str:
    """Resolve per-subscription frequency against user default."""
    sub = (sub_freq or "default").strip().lower()
    if sub and sub != "default":
        return sub
    user = (user_freq or "daily").strip().lower()
    return user if user in ("realtime", "daily") else "daily"
