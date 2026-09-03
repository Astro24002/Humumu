"""Unit tests for feed URL normalization."""

from app.services.feed_url import normalize_feed_url


def test_lowercase_host_and_strip_slash():
    assert normalize_feed_url("HTTPS://Example.COM/Feed/") == "https://example.com/Feed"


def test_strip_fragment():
    assert normalize_feed_url("https://example.com/a.rss#x") == "https://example.com/a.rss"


def test_default_https_port():
    assert normalize_feed_url("https://example.com:443/a.rss") == "https://example.com/a.rss"


def test_default_http_port():
    assert normalize_feed_url("http://example.com:80/a.rss") == "http://example.com/a.rss"


def test_keep_non_default_port():
    assert normalize_feed_url("https://example.com:8443/a.rss") == "https://example.com:8443/a.rss"


def test_empty():
    assert normalize_feed_url("") == ""
