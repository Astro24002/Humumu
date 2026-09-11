"""Unit tests for push copy helpers and email/wechat body builders."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services import notify_content as nc
from app.services.notifier_email import (
    EmailNotifier,
    _render_article_html,
    _render_article_text,
    _render_summary_html,
)
from app.services.notifier_wechat import WeChatNotifier


def test_clean_abstract_strips_arxiv_prefix():
    raw = "arXiv:1234.5678 Announce Type: new\nAbstract: Hello world"
    assert nc.clean_abstract(raw) == "Hello world"
    assert nc.clean_abstract("") == ""
    assert nc.clean_abstract(None) == ""


def test_is_real_email():
    assert nc.is_real_email("a@example.com")
    assert not nc.is_real_email("")
    assert not nc.is_real_email("ox@wechat.user")
    assert not nc.is_real_email("OX@WeChat.User")


def test_format_authors_and_reasons():
    assert nc.format_authors(["A", "B", "C", "D"], max_n=3) == "A, B, C 等"
    assert nc.format_authors(["A"]) == "A"
    assert nc.format_reasons("journal,keyword") == "期刊、关键词"
    assert nc.format_reasons(["author", "author", "journal"]) == "作者、期刊"


def test_article_link_prefers_url_then_doi():
    assert nc.article_link("https://ex.com/p", "10.1/x") == "https://ex.com/p"
    assert nc.article_link("", "10.1/x") == "https://doi.org/10.1/x"
    assert nc.article_link(None, None) == ""


def test_email_subjects_zh():
    sub = nc.email_realtime_subject("Nature", "A very long title " * 10)
    assert sub.startswith("【Nature】新论文：")
    assert "Daily" not in sub
    assert "Humumu" in nc.email_digest_subject(3, date_label="2026-09-11")


def test_render_article_html_escapes_and_includes_reasons():
    html = _render_article_html(
        journal_name="J <script>",
        title="T & Co",
        authors=["Alice", "Bob", "Carol", "Dan"],
        abstract="arXiv:1 Announce Type: new\nAbstract: Body",
        url="https://ex.com/a",
        doi="10.1/x",
        match_reasons="journal,keyword",
        settings_href="https://app.example/settings",
        app_href="https://app.example/articles/1",
    )
    assert "<script>" not in html
    assert "J &lt;script&gt;" in html
    assert "T &amp; Co" in html
    assert "匹配原因：期刊、关键词" in html
    assert "阅读全文" in html
    assert "管理推送设置" in html
    assert "Body" in html
    text = _render_article_text(
        journal_name="J",
        title="T",
        authors=["Alice"],
        abstract="Abs",
        url="https://ex.com/a",
        doi="",
        match_reasons=["author"],
    )
    assert "匹配原因：作者" in text
    assert "阅读全文：https://ex.com/a" in text


def test_render_summary_caps_and_zh():
    arts = [
        {
            "title": f"Paper {i}",
            "journal_name": "J",
            "url": f"https://ex.com/{i}",
            "authors": ["A"],
        }
        for i in range(45)
    ]
    html = _render_summary_html(arts, settings_href="https://app/settings", date_label="2026-09-11")
    assert "每日汇总" in html
    assert "还有 5 篇" in html
    assert html.count("<li") == 40


def test_email_notifier_skips_stub_and_sends_multipart():
    settings = MagicMock()
    settings.smtp_host = "smtp.example.com"
    settings.smtp_port = 587
    settings.smtp_user = "u"
    settings.smtp_pass = "p"
    settings.smtp_from = "from@example.com"
    settings.public_app_url = "https://app.example"

    ntfr = EmailNotifier(settings)
    assert ntfr.send_article(
        to_email="ox@wechat.user",
        journal_name="J",
        title="T",
        authors=[],
        abstract="",
        url="",
        doi="",
    ) is False

    with patch.object(ntfr, "_send_multipart") as send:
        ok = ntfr.send_article(
            to_email="a@example.com",
            journal_name="Nature",
            title="Hello",
            authors=["A"],
            abstract="Abs",
            url="https://ex.com",
            doi="10.1/x",
            match_reasons="journal",
            article_id="aid-1",
        )
        assert ok is True
        send.assert_called_once()
        _to, subject, text, html = send.call_args[0]
        assert "【Nature】新论文" in subject
        assert "匹配原因：期刊" in text
        assert "阅读全文" in html


@pytest.mark.asyncio
async def test_wechat_send_article_payload_and_page():
    settings = MagicMock()
    settings.wechat_appid = "app"
    settings.wechat_secret = "sec"
    settings.wechat_template_realtime = "TPL_RT"
    settings.wechat_template_daily = "TPL_D"

    ntfr = WeChatNotifier(settings)
    with (
        patch.object(ntfr, "_get_access_token", return_value="tok"),
        patch.object(ntfr, "_post_template") as post,
    ):
        post.return_value = None
        ok = await ntfr.send_article(
            openid="ox",
            journal_name="Nature",
            title="A" * 200,
            authors=["Alice", "Bob", "Carol"],
            abstract="",
            doi="",
            url="https://ex.com/p",
            match_reasons="keyword",
            article_id="abc-123",
        )
        assert ok is True
        args, kwargs = post.call_args
        assert args[1] == "ox"
        assert args[2] == "TPL_RT"
        data = args[3]
        assert data["title"]["value"]
        assert "…" in data["title"]["value"] or len(data["title"]["value"]) <= 80
        # empty abstract still non-empty slot
        assert data["abstract"]["value"]
        assert kwargs.get("page") == "pages/article/detail?id=abc-123"


@pytest.mark.asyncio
async def test_wechat_summary_has_page_and_count():
    settings = MagicMock()
    settings.wechat_appid = "app"
    settings.wechat_secret = "sec"
    settings.wechat_template_realtime = "TPL_RT"
    settings.wechat_template_daily = "TPL_D"
    ntfr = WeChatNotifier(settings)
    arts = [
        {"title": "T1", "journal_name": "J1"},
        {"title": "T2", "journal_name": "J2"},
        {"title": "T3", "journal_name": "J3"},
        {"title": "T4", "journal_name": "J4"},
    ]
    with (
        patch.object(ntfr, "_get_access_token", return_value="tok"),
        patch.object(ntfr, "_post_template") as post,
    ):
        post.return_value = None
        ok = await ntfr.send_summary(openid="ox", articles=arts, date_label="2026-09-11")
        assert ok is True
        args, kwargs = post.call_args
        data = args[3]
        assert "4" in data["count"]["value"]
        assert kwargs.get("page") == "pages/index/index"
