"""Unit tests for daily digest article selection (journal ∪ author ∪ keyword)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.jobs.daily_summary import select_digest_articles


def _art(**kw):
    base = {
        "id": str(uuid4()),
        "journal_id": "j-daily",
        "title": "Quantum widgets",
        "url": "https://ex.com/p",
        "doi": "10.1/x",
        "authors": ["Alice Smith"],
        "abstract": "About quantum computing.",
        "journal_name": "Nature",
        "fetched_at": datetime(2026, 9, 11, tzinfo=timezone.utc),
    }
    base.update(kw)
    return base


def test_digest_includes_daily_journal_and_skips_realtime_override():
    daily = _art(id="a1", journal_id="j1", title="Daily journal paper")
    realtime = _art(id="a2", journal_id="j2", title="Realtime journal paper")
    out = select_digest_articles(
        user_id="u1",
        user_push_freq="daily",
        articles=[daily, realtime],
        journal_subs=[("j1", "default"), ("j2", "realtime")],
        tracked_authors=[],
        keywords=[],
    )
    assert [a["id"] for a in out] == ["a1"]
    assert out[0]["match_reasons"] == ["journal"]


def test_digest_includes_author_and_keyword_hits_without_journal_sub():
    author_hit = _art(
        id="a-auth",
        journal_id="j-other",
        title="Unrelated",
        authors=["Bob Jones"],
        abstract="",
    )
    kw_hit = _art(
        id="a-kw",
        journal_id="j-other",
        title="Advances in Quantum Computing",
        authors=["Carol"],
        abstract="",
    )
    miss = _art(
        id="a-miss",
        journal_id="j-other",
        title="Something else",
        authors=["Nobody"],
        abstract="nothing",
    )
    out = select_digest_articles(
        user_id="u1",
        user_push_freq="daily",
        articles=[author_hit, kw_hit, miss],
        journal_subs=[],
        tracked_authors=["bob jones"],
        keywords=["quantum"],
    )
    by_id = {a["id"]: a for a in out}
    assert set(by_id) == {"a-auth", "a-kw"}
    assert by_id["a-auth"]["match_reasons"] == ["author"]
    assert by_id["a-kw"]["match_reasons"] == ["keyword"]


def test_digest_unions_reasons_and_dedupes():
    a = _art(
        id="same",
        journal_id="j1",
        title="Quantum widgets",
        authors=["Alice Smith"],
        abstract="quantum",
    )
    out = select_digest_articles(
        user_id="u1",
        user_push_freq="daily",
        articles=[a],
        journal_subs=[("j1", "default")],
        tracked_authors=["alice smith"],
        keywords=["quantum"],
    )
    assert len(out) == 1
    assert out[0]["match_reasons"] == ["journal", "author", "keyword"]


def test_digest_empty_when_nothing_matches():
    out = select_digest_articles(
        user_id="u1",
        user_push_freq="daily",
        articles=[_art(title="Nope", authors=["X"], abstract="z")],
        journal_subs=[],
        tracked_authors=["nobody"],
        keywords=["missing"],
    )
    assert out == []


def test_digest_user_realtime_still_honors_daily_journal_override():
    a = _art(id="a1", journal_id="j1")
    out = select_digest_articles(
        user_id="u1",
        user_push_freq="realtime",
        articles=[a],
        journal_subs=[("j1", "daily")],
        tracked_authors=[],
        keywords=[],
    )
    assert [x["id"] for x in out] == ["a1"]
