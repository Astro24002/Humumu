"""Unit tests for pure matcher helpers."""

from app.services.matcher import (
    MatchResult,
    apply_channels,
    dedupe_by_user,
    match_article,
    match_authors,
    match_keywords,
    resolve_channel,
)


def test_author_casefold_equality():
    results = match_authors(
        article_id="a1",
        article_authors=["Alice Smith", "Bob Jones"],
        tracked=[
            ("u1", "alice smith"),
            ("u2", "ALICE SMITH"),
            ("u3", "Nobody"),
            ("u4", " bob jones "),
        ],
    )
    user_ids = {r.user_id for r in results}
    assert user_ids == {"u1", "u2", "u4"}
    assert all(r.article_id == "a1" for r in results)


def test_author_no_match_empty():
    assert match_authors(article_id="a1", article_authors=[], tracked=[("u1", "x")]) == []
    assert (
        match_authors(article_id="a1", article_authors=["Alice"], tracked=[]) == []
    )


def test_keyword_substring_title_and_abstract():
    results = match_keywords(
        article_id="a1",
        title="Advances in Quantum Computing",
        abstract="This paper studies widget calibration methods.",
        keywords=[
            ("u1", "quantum"),
            ("u2", "WIDGET"),
            ("u3", "missing"),
            ("u4", "Computing"),
        ],
    )
    user_ids = {r.user_id for r in results}
    assert user_ids == {"u1", "u2", "u4"}


def test_keyword_empty_fields():
    assert (
        match_keywords(
            article_id="a1", title="", abstract="", keywords=[("u1", "x")]
        )
        == []
    )


def test_dedupe_users():
    results = [
        MatchResult(user_id="u1", article_id="a1"),
        MatchResult(user_id="u2", article_id="a1"),
        MatchResult(user_id="u1", article_id="a1"),
        MatchResult(user_id="u3", article_id="a1"),
        MatchResult(user_id="u2", article_id="a1"),
    ]
    deduped = dedupe_by_user(results)
    assert [r.user_id for r in deduped] == ["u1", "u2", "u3"]


def test_resolve_channel():
    assert resolve_channel("openid-abc") == "wechat"
    assert resolve_channel("  ") == "email"
    assert resolve_channel(None) == "email"
    assert resolve_channel("") == "email"


def test_apply_channels():
    results = [
        MatchResult(user_id="u1", article_id="a1"),
        MatchResult(user_id="u2", article_id="a1"),
    ]
    out = apply_channels(
        results,
        {"u1": "oxxx", "u2": None},
    )
    assert out[0].channel == "wechat"
    assert out[1].channel == "email"


def test_match_article_union_and_dedupe():
    """Journal + author + keyword; same user once; channel resolved."""
    results = match_article(
        article_id="art-1",
        journal_subscriber_ids=["u1", "u2"],
        article_authors=["Alice Smith"],
        title="Quantum widgets forever",
        abstract="Boring abstract",
        tracked_authors=[("u1", "alice smith"), ("u3", "nobody")],
        keywords=[("u2", "quantum"), ("u4", "widgets")],
        user_openid={
            "u1": "openid-1",
            "u2": None,
            "u4": "openid-4",
        },
    )
    by_user = {r.user_id: r for r in results}
    # u1 journal+author, u2 journal+keyword, u4 keyword only; u3 no match
    assert set(by_user) == {"u1", "u2", "u4"}
    assert by_user["u1"].channel == "wechat"
    assert by_user["u2"].channel == "email"
    assert by_user["u4"].channel == "wechat"
    assert all(r.article_id == "art-1" for r in results)
