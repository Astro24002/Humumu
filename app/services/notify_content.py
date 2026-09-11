"""Shared helpers for email / WeChat push copy (ZH-first product tone)."""

from __future__ import annotations

import html
import re
from typing import Sequence
from urllib.parse import quote

# arXiv announce noise, same idea as web/miniprogram cleanAbstract
_ARXIV_PREFIX = re.compile(
    r"^arXiv:\S+\s+Announce Type:\s*\S+\s*\n\s*Abstract:\s*",
    re.IGNORECASE,
)

_REASON_LABELS = {
    "journal": "期刊",
    "author": "作者",
    "keyword": "关键词",
}

_WECHAT_STUB_SUFFIX = "@wechat.user"


def is_real_email(email: str | None) -> bool:
    """True when email looks deliverable (not empty / WeChat placeholder)."""
    e = (email or "").strip()
    if not e or "@" not in e:
        return False
    if e.lower().endswith(_WECHAT_STUB_SUFFIX):
        return False
    return True


def clean_abstract(text: str | None) -> str:
    if not text:
        return ""
    cleaned = _ARXIV_PREFIX.sub("", text.strip())
    # collapse excessive whitespace for push bodies
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def truncate(s: str, max_len: int) -> str:
    s = s or ""
    if max_len <= 0:
        return ""
    if len(s) <= max_len:
        return s
    if max_len <= 1:
        return s[:max_len]
    return s[: max_len - 1] + "…"


def format_authors(authors: Sequence[str] | None, max_n: int = 3) -> str:
    list_ = [a.strip() for a in (authors or []) if a and str(a).strip()]
    if not list_:
        return ""
    head = ", ".join(list_[:max_n])
    return f"{head} 等" if len(list_) > max_n else head


def reason_labels(reasons: Sequence[str] | str | None) -> list[str]:
    if reasons is None:
        return []
    if isinstance(reasons, str):
        parts = [p.strip() for p in reasons.split(",") if p.strip()]
    else:
        parts = [str(p).strip() for p in reasons if str(p).strip()]
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        label = _REASON_LABELS.get(p, p)
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def format_reasons(reasons: Sequence[str] | str | None) -> str:
    labels = reason_labels(reasons)
    return "、".join(labels) if labels else ""


def article_link(url: str | None, doi: str | None = None) -> str:
    """Prefer original URL; fall back to doi.org when DOI present."""
    u = (url or "").strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    d = (doi or "").strip()
    if d:
        d = d.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
        d = d.removeprefix("doi:").strip()
        if d:
            return f"https://doi.org/{d}"
    return ""


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def settings_url(public_app_url: str | None) -> str:
    base = (public_app_url or "").rstrip("/")
    if not base:
        return ""
    return f"{base}/settings"


def article_app_url(public_app_url: str | None, article_id: str | None) -> str:
    base = (public_app_url or "").rstrip("/")
    if not base or not article_id:
        return ""
    return f"{base}/articles/{article_id}"


def wechat_article_page(article_id: str | None) -> str:
    """Mini-program path opened from subscribe message."""
    if not article_id:
        return "pages/index/index"
    return f"pages/article/detail?id={quote(str(article_id), safe='')}"


def wechat_digest_page() -> str:
    return "pages/index/index"


def wechat_thing(value: str, *, empty: str = "—", max_len: int = 20) -> dict[str, str]:
    """
    Build a WeChat subscribe-message data item.

    Mini-program thing.DATA is typically short; we keep a conservative default
    and always send a non-empty value (empty slots often get API rejects).
    """
    v = (value or "").strip() or empty
    return {"value": truncate(v, max_len)}


def email_realtime_subject(journal_name: str, title: str) -> str:
    jn = (journal_name or "").strip() or "Humumu"
    t = truncate((title or "").strip() or "新论文", 60)
    return f"【{jn}】新论文：{t}"


def email_digest_subject(count: int, *, date_label: str = "") -> str:
    if date_label:
        return f"Humumu 每日汇总（{date_label}）：{count} 篇新论文"
    return f"Humumu 每日汇总：{count} 篇新论文"
