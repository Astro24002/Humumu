"""Fetch feed title/metadata for journal preview (SSRF-safe httpx + feedparser)."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

import feedparser

from app.services.url_safety import UnsafeURLError, safe_get_text

_TIMEOUT = 15.0
_MAX_PREVIEW_ITEMS = 5


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def _title_from_xml(body: str) -> str | None:
    """XML heuristics mirroring Go FetchFeedMeta (atom / rdf / rss channel title)."""
    peek = body
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None

    root_local = _strip_ns(root.tag).lower()

    # Atom: <feed><title>
    if root_local == "feed" or "<feed" in peek or "<Feed" in peek:
        for child in root:
            if _strip_ns(child.tag).lower() == "title":
                t = _text(child)
                if t:
                    return t
        for el in root.iter():
            if _strip_ns(el.tag).lower() == "title":
                t = _text(el)
                if t:
                    return t

    # RDF / RSS: channel/title
    for el in root.iter():
        if _strip_ns(el.tag).lower() == "channel":
            for child in el:
                if _strip_ns(child.tag).lower() == "title":
                    t = _text(child)
                    if t:
                        return t

    for child in root:
        if _strip_ns(child.tag).lower() == "title":
            t = _text(child)
            if t:
                return t

    return None


def _title_from_feedparser(body: str) -> str | None:
    parsed = feedparser.parse(body)
    title = (getattr(parsed, "feed", {}) or {}).get("title") or ""
    title = str(title).strip()
    return title or None


def _preview_items(body: str, limit: int = _MAX_PREVIEW_ITEMS) -> list[dict[str, str]]:
    parsed = feedparser.parse(body)
    items: list[dict[str, str]] = []
    for entry in getattr(parsed, "entries", []) or []:
        title = ""
        if hasattr(entry, "get"):
            title = (entry.get("title") or "").strip()
        if not title:
            title = str(getattr(entry, "title", "") or "").strip()
        link = ""
        if hasattr(entry, "get"):
            link = (entry.get("link") or "").strip()
        if not link:
            link = str(getattr(entry, "link", "") or "").strip()
        published = ""
        for key in ("published", "updated"):
            raw = getattr(entry, key, None) or (entry.get(key) if hasattr(entry, "get") else None)
            if raw:
                published = str(raw).strip()
                break
        if not title and not link:
            continue
        items.append({"title": title, "url": link, "published": published})
        if len(items) >= limit:
            break
    return items


async def fetch_feed_meta(url: str) -> dict:
    """
    Fetch a feed URL and return metadata.

    Returns:
        {"name": <title>, "title": <title>, "source_type": "rss", "items": [...]}

    Raises:
        UnsafeURLError on SSRF rejection.
        Exception on network/HTTP/parse failure (caller maps to 400).
    """
    try:
        _final, body, _hdrs = await safe_get_text(url, timeout=_TIMEOUT)
    except UnsafeURLError:
        raise
    except Exception as exc:
        raise ValueError(f"feed meta fetch failed: {exc}") from exc

    if not body:
        raise ValueError(f"empty feed body from {url}")

    title = _title_from_feedparser(body) or _title_from_xml(body)
    if not title:
        m = re.search(
            r"<channel[^>]*>.*?<title[^>]*>(.*?)</title>",
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not m:
            m = re.search(
                r"<feed[^>]*>.*?<title[^>]*>(.*?)</title>",
                body,
                flags=re.IGNORECASE | re.DOTALL,
            )
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

    if not title:
        raise ValueError(f"cannot determine feed title from {url}")

    return {
        "name": title,
        "title": title,
        "source_type": "rss",
        "items": _preview_items(body),
    }
