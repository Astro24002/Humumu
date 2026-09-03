"""Unit tests for SSRF-safe URL validation."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.url_safety import UnsafeURLError, validate_public_http_url


def test_rejects_non_http():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("file:///etc/passwd")


def test_rejects_ftp():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("ftp://example.com/a")


def test_rejects_localhost():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://localhost/x")


def test_rejects_127():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://127.0.0.1/x")


def test_rejects_private_ip():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://192.168.1.1/x")


def test_rejects_10_network():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://10.0.0.5/x")


def test_rejects_metadata_ip():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://169.254.169.254/latest/meta-data")


def test_rejects_empty():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("")


def test_rejects_credentials():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("https://user:pass@8.8.8.8/x")


def test_allows_public_literal():
    assert validate_public_http_url("https://8.8.8.8/robots.txt").startswith("https://")


def test_rejects_hostname_resolving_to_private():
    # mock getaddrinfo to return a private IP for evil.example
    private = ("192.168.0.10", 0)
    with patch(
        "app.services.url_safety.socket.getaddrinfo",
        return_value=[(None, None, None, None, private)],
    ):
        with pytest.raises(UnsafeURLError):
            validate_public_http_url("https://evil.example/feed")


def test_allows_hostname_resolving_to_public():
    public = ("8.8.8.8", 0)
    with patch(
        "app.services.url_safety.socket.getaddrinfo",
        return_value=[(None, None, None, None, public)],
    ):
        out = validate_public_http_url("https://feeds.example.com/rss")
        assert out.startswith("https://")
