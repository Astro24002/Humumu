"""Fetcher parse tests using fixture RSS XML (no network)."""

from pathlib import Path

from app.services.fetcher import parse_feed_body

FIXTURE = Path(__file__).parent / "fixtures" / "sample_rss.xml"


def test_parse_rss_titles_and_links():
    body = FIXTURE.read_text(encoding="utf-8")
    articles = parse_feed_body(body)
    assert len(articles) == 3

    titles = [a["title"] for a in articles]
    assert titles[0] == "Alpha Paper on Quantum Widgets"
    assert titles[1] == "Beta Study Without DOI"
    assert titles[2] == "Gamma Review"

    assert articles[0]["url"] == "https://doi.org/10.1000/alpha.1"
    assert articles[1]["url"] == "https://example.org/articles/beta-study"
    assert articles[2]["url"] == "https://example.org/gamma"


def test_parse_rss_doi_from_link():
    body = FIXTURE.read_text(encoding="utf-8")
    articles = parse_feed_body(body)
    assert articles[0]["doi"] == "10.1000/alpha.1"
    # no doi in link
    assert articles[1]["doi"] in (None, "")
    assert articles[2]["doi"] in (None, "")


def test_parse_rss_authors_and_abstract():
    body = FIXTURE.read_text(encoding="utf-8")
    articles = parse_feed_body(body)

    assert "Alice Smith" in articles[0]["authors"]
    assert "Bob Jones" in articles[0]["authors"]
    assert "quantum widgets" in articles[0]["abstract"].lower()
    # HTML stripped
    assert "<b>" not in articles[0]["abstract"]

    assert articles[1]["authors"] == ["Carol Lee"]
    assert "beta" in articles[1]["abstract"].lower()

    assert "Dana Wu" in articles[2]["authors"]
    assert "<i>" not in articles[2]["abstract"]


def test_parse_rss_publish_dates():
    body = FIXTURE.read_text(encoding="utf-8")
    articles = parse_feed_body(body)
    # feedparser should extract structured dates
    assert articles[0]["publish_date"] == "2024-06-15"
    assert articles[1]["publish_date"] == "2024-07-01"


def test_parse_empty_feed():
    body = """<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>"""
    assert parse_feed_body(body) == []
