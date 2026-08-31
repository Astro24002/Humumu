"""Fetch and parse journal feeds (RSS / Atom / CNKI-as-RSS) into RawArticle dicts."""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any, TypedDict

import feedparser
import httpx

logger = logging.getLogger(__name__)

_USER_AGENT = "JournalMonitor/1.0"
_TIMEOUT = 30.0


class RawArticle(TypedDict):
    title: str
    url: str
    doi: str | None
    authors: list[str]
    abstract: str
    publish_date: str  # "YYYY-MM-DD" or ""


def _strip_html(text: str) -> str:
    if not text:
        return ""
    no_tags = re.sub(r"<[^>]+>", "", text)
    return unescape(no_tags).strip()


def _extract_doi_from_url(url: str) -> str:
    if not url:
        return ""
    if "doi.org/" in url:
        parts = url.split("doi.org/", 1)
        if len(parts) == 2:
            return parts[1].strip()
    return ""


def _split_authors(author_str: str) -> list[str]:
    if not author_str:
        return []
    return [p.strip() for p in author_str.split(",") if p.strip()]


def _authors_from_entry(entry: Any) -> list[str]:
    authors: list[str] = []
    # feedparser may expose entry.authors as list of dicts
    raw_authors = None
    if hasattr(entry, "get"):
        raw_authors = entry.get("authors")
    if not raw_authors:
        raw_authors = getattr(entry, "authors", None)
    if raw_authors:
        for a in raw_authors:
            if isinstance(a, dict):
                name = (a.get("name") or "").strip()
            else:
                name = str(getattr(a, "name", a) or "").strip()
            if name:
                # dc:creator often packs "A, B" into one author name
                authors.extend(_split_authors(name) if "," in name else [name])
        if authors:
            return authors

    # dc:creator / author single field
    author = ""
    if hasattr(entry, "get"):
        author = entry.get("author") or entry.get("dc_creator") or ""
    if not author:
        author = getattr(entry, "author", None) or getattr(entry, "dc_creator", None) or ""
    if author:
        return _split_authors(str(author))

    return []

def _entry_doi(entry: Any, link: str) -> str | None:
    doi = ""
    # prism/dc or custom doi fields
    for key in ("doi", "dc_identifier", "id"):
        val = entry.get(key) if hasattr(entry, "get") else getattr(entry, key, None)
        if not val:
            continue
        s = str(val).strip()
        if s.lower().startswith("doi:"):
            s = s[4:].strip()
        if "doi.org/" in s:
            s = _extract_doi_from_url(s)
        # crude DOI shape
        if "/" in s and not s.startswith("http"):
            doi = s
            break
        if key == "id" and "doi.org/" in str(val):
            doi = _extract_doi_from_url(str(val))
            if doi:
                break

    if not doi:
        doi = _extract_doi_from_url(link)

    doi = (doi or "").strip()
    return doi or None


def _entry_date(entry: Any) -> str:
    """Return YYYY-MM-DD if parseable, else empty string."""
    # prefer published_parsed / updated_parsed (time.struct_time)
    for key in ("published_parsed", "updated_parsed"):
        st = getattr(entry, key, None) or (entry.get(key) if hasattr(entry, "get") else None)
        if st and getattr(st, "tm_year", None):
            try:
                return f"{st.tm_year:04d}-{st.tm_mon:02d}-{st.tm_mday:02d}"
            except Exception:  # noqa: BLE001
                pass

    for key in ("published", "updated", "dc_date", "date"):
        raw = getattr(entry, key, None) or (entry.get(key) if hasattr(entry, "get") else None)
        if not raw:
            continue
        s = str(raw).strip()
        # ISO date prefix
        m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
        if m:
            return m.group(1)
    return ""


def _entry_abstract(entry: Any) -> str:
    summary = ""
    if hasattr(entry, "get"):
        summary = entry.get("summary") or entry.get("description") or ""
    if not summary:
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    abstract = _strip_html(str(summary))
    # arXiv-style: "... Abstract: ..."
    if "Abstract:" in abstract:
        parts = abstract.split("Abstract:")
        abstract = parts[-1].strip()
    return abstract


def parse_feed_body(body: str | bytes) -> list[RawArticle]:
    """Parse feed XML/bytes into RawArticle list (no network)."""
    parsed = feedparser.parse(body)
    articles: list[RawArticle] = []
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
        # atom alternate links
        if not link and hasattr(entry, "get"):
            links = entry.get("links") or []
            for l in links:
                if isinstance(l, dict) and l.get("href"):
                    rel = l.get("rel") or "alternate"
                    if rel in ("alternate", ""):
                        link = l["href"]
                        break
            if not link and links and isinstance(links[0], dict):
                link = links[0].get("href") or ""

        doi = _entry_doi(entry, link)
        authors = _authors_from_entry(entry)
        abstract = _entry_abstract(entry)
        publish_date = _entry_date(entry)

        if not doi and not title:
            continue

        articles.append(
            RawArticle(
                title=title,
                url=link or "",
                doi=doi,
                authors=authors,
                abstract=abstract,
                publish_date=publish_date,
            )
        )
    return articles


async def fetch_articles(source_url: str, source_type: str = "rss") -> list[RawArticle]:
    """
    HTTP GET feed and parse into RawArticle list.

    ``source_type`` of ``rss`` and ``cnki`` both use RSS/Atom parsing.
    """
    st = (source_type or "rss").lower()
    if st not in ("rss", "cnki", "atom", "rdf"):
        logger.warning("unsupported source_type %s; attempting RSS parse", source_type)

    headers = {"User-Agent": _USER_AGENT}
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(source_url, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"feed status {resp.status_code} for {source_url}")
        body = resp.content

    return parse_feed_body(body)
