"""Fetch feed title/metadata for journal preview (httpx + feedparser)."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

import feedparser
import httpx

_USER_AGENT = "JournalMonitor/1.0"
_TIMEOUT = 30.0


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
        # nested search
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

    # Direct title on root channel-like docs
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


async def fetch_feed_meta(url: str) -> dict[str, str]:
    """
    Fetch a feed URL and return metadata.

    Returns:
        {"name": <title>, "title": <title>, "source_type": "rss"}

    Raises:
        Exception on network/HTTP/parse failure (caller maps to 400).
    """
    headers = {"User-Agent": _USER_AGENT}
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"feed meta status {resp.status_code}")
        body = resp.text

    title = _title_from_feedparser(body) or _title_from_xml(body)
    if not title:
        # last-ditch regex for <title>...</title> inside channel/feed
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

    return {"name": title, "title": title, "source_type": "rss"}
