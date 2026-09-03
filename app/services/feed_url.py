"""Normalize feed URLs for dedup lookup."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_feed_url(url: str) -> str:
    """
    Normalize a feed URL for comparison/storage.

    - lowercase scheme and host
    - strip default ports (80/443)
    - remove fragment
    - strip trailing slash on path (except root)
    - drop empty query; keep non-empty query as sorted key=value pairs
    """
    raw = (url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    if not host:
        return raw

    port = parsed.port
    if port is not None:
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            netloc = host
        else:
            netloc = f"{host}:{port}"
    else:
        netloc = host

    # Preserve userinfo only if present (normally rejected by SSRF layer)
    if parsed.username:
        user = parsed.username
        if parsed.password:
            user = f"{user}:{parsed.password}"
        netloc = f"{user}@{netloc}"

    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query = ""
    if parsed.query:
        pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k]
        if pairs:
            pairs.sort()
            query = urlencode(pairs)

    return urlunparse((scheme, netloc, path, "", query, ""))
