"""SMTP email notifier. Skips cleanly when SMTP host is empty."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Sequence

from app.config import Settings
from app.services import notify_content as nc

logger = logging.getLogger(__name__)

_DIGEST_LIST_CAP = 40


def _render_article_html(
    *,
    journal_name: str,
    title: str,
    authors: Sequence[str],
    abstract: str,
    url: str,
    doi: str,
    match_reasons: Sequence[str] | str | None = None,
    settings_href: str = "",
    app_href: str = "",
) -> str:
    jn = nc.esc(journal_name or "来源")
    t = nc.esc(title or "（无标题）")
    authors_display = nc.esc(nc.format_authors(authors))
    abs_clean = nc.clean_abstract(abstract)
    abs_html = nc.esc(nc.truncate(abs_clean, 800)) if abs_clean else ""
    link = nc.article_link(url, doi)
    link_esc = nc.esc(link) if link else ""
    doi_s = (doi or "").strip()
    reasons = nc.format_reasons(match_reasons)

    reason_block = ""
    if reasons:
        reason_block = (
            f'<p style="color:#16a34a;font-size:13px;margin:8px 0 0;">'
            f"匹配原因：{nc.esc(reasons)}</p>"
        )

    authors_block = (
        f'<p style="color:#64748b;font-size:14px;margin:4px 0 12px;">{authors_display}</p>'
        if authors_display
        else ""
    )
    abstract_block = (
        f'<p style="color:#334155;line-height:1.6;font-size:14px;">{abs_html}</p>'
        if abs_html
        else '<p style="color:#94a3b8;font-size:13px;">（暂无摘要）</p>'
    )

    cta = ""
    if link_esc:
        cta = (
            f'<a href="{link_esc}" style="display:inline-block;background:#16a34a;color:#fff;'
            f'padding:10px 18px;text-decoration:none;border-radius:6px;font-size:14px;">'
            f"阅读全文</a>"
        )
    elif app_href:
        cta = (
            f'<a href="{nc.esc(app_href)}" style="display:inline-block;background:#16a34a;color:#fff;'
            f'padding:10px 18px;text-decoration:none;border-radius:6px;font-size:14px;">'
            f"在 Humumu 中查看</a>"
        )

    doi_block = ""
    if doi_s:
        doi_href = nc.esc(f"https://doi.org/{doi_s.removeprefix('https://doi.org/').removeprefix('http://doi.org/')}")
        doi_block = (
            f' <span style="color:#64748b;font-size:13px;margin-left:12px;">'
            f'DOI: <a href="{doi_href}" style="color:#2563eb;">{nc.esc(doi_s)}</a></span>'
        )

    footer_bits: list[str] = []
    if settings_href:
        footer_bits.append(
            f'<a href="{nc.esc(settings_href)}" style="color:#64748b;">管理推送设置</a>'
        )
    if app_href and link_esc:
        footer_bits.append(
            f'<a href="{nc.esc(app_href)}" style="color:#64748b;">在 Humumu 打开</a>'
        )
    footer = (
        f'<p style="margin-top:28px;padding-top:16px;border-top:1px solid #e2e8f0;'
        f'color:#94a3b8;font-size:12px;">{" · ".join(footer_bits) if footer_bits else "Humumu 学术订阅"}'
        f"<br/>本邮件由 Humumu 根据你的订阅自动发送。</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8" /></head>
<body style="margin:0;padding:0;background:#f8fafc;">
  <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;
              max-width:640px;margin:0 auto;padding:24px 16px;color:#0f172a;">
    <p style="color:#16a34a;font-size:12px;font-weight:600;letter-spacing:0.04em;margin:0 0 8px;">HUMUMU · 新论文提醒</p>
    <h2 style="color:#0f172a;font-size:15px;font-weight:600;margin:0 0 4px;">{jn}</h2>
    <h1 style="color:#0f172a;font-size:20px;line-height:1.35;margin:0 0 8px;font-weight:700;">{t}</h1>
    {authors_block}
    {reason_block}
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0;" />
    {abstract_block}
    <p style="margin:20px 0 0;">{cta}{doi_block}</p>
    {footer}
  </div>
</body>
</html>"""


def _render_article_text(
    *,
    journal_name: str,
    title: str,
    authors: Sequence[str],
    abstract: str,
    url: str,
    doi: str,
    match_reasons: Sequence[str] | str | None = None,
    settings_href: str = "",
    app_href: str = "",
) -> str:
    lines = [
        "Humumu · 新论文提醒",
        "",
        journal_name or "来源",
        title or "（无标题）",
    ]
    authors_s = nc.format_authors(authors)
    if authors_s:
        lines.append(authors_s)
    reasons = nc.format_reasons(match_reasons)
    if reasons:
        lines.append(f"匹配原因：{reasons}")
    lines.append("")
    abs_clean = nc.clean_abstract(abstract)
    lines.append(nc.truncate(abs_clean, 600) if abs_clean else "（暂无摘要）")
    link = nc.article_link(url, doi)
    lines.append("")
    if link:
        lines.append(f"阅读全文：{link}")
    elif app_href:
        lines.append(f"在 Humumu 查看：{app_href}")
    if doi:
        lines.append(f"DOI：{doi}")
    if settings_href:
        lines.append("")
        lines.append(f"管理推送设置：{settings_href}")
    lines.append("")
    lines.append("本邮件由 Humumu 根据你的订阅自动发送。")
    return "\n".join(lines)


def _render_summary_html(
    articles: Sequence[dict[str, Any]],
    *,
    settings_href: str = "",
    date_label: str = "",
) -> str:
    total = len(articles)
    shown = list(articles[:_DIGEST_LIST_CAP])
    items: list[str] = []
    for a in shown:
        jn = nc.esc(a.get("journal_name") or "")
        title = nc.esc(a.get("title") or "（无标题）")
        link = nc.article_link(a.get("url"), a.get("doi"))
        authors_s = nc.esc(nc.format_authors(a.get("authors") or [], max_n=2))
        meta = jn
        if authors_s:
            meta = f"{jn} · {authors_s}" if jn else authors_s
        if link:
            title_html = f'<a href="{nc.esc(link)}" style="color:#0f172a;text-decoration:none;font-weight:600;">{title}</a>'
        else:
            title_html = f'<span style="font-weight:600;">{title}</span>'
        items.append(
            f'<li style="margin:0 0 12px;line-height:1.45;">'
            f"{title_html}"
            f'<div style="color:#64748b;font-size:12px;margin-top:2px;">{meta}</div>'
            f"</li>"
        )
    extra = ""
    if total > len(shown):
        extra = (
            f'<p style="color:#64748b;font-size:13px;">还有 {total - len(shown)} 篇未列出，'
            f"请登录 Humumu 查看完整更新。</p>"
        )
    date_line = f"（{nc.esc(date_label)}）" if date_label else ""
    footer = ""
    if settings_href:
        footer = (
            f'<p style="margin-top:24px;padding-top:16px;border-top:1px solid #e2e8f0;'
            f'color:#94a3b8;font-size:12px;">'
            f'<a href="{nc.esc(settings_href)}" style="color:#64748b;">管理推送设置</a>'
            f" · Humumu 每日汇总</p>"
        )
    else:
        footer = (
            '<p style="margin-top:24px;padding-top:16px;border-top:1px solid #e2e8f0;'
            'color:#94a3b8;font-size:12px;">Humumu 每日汇总</p>'
        )
    lis = "\n".join(items)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8" /></head>
<body style="margin:0;padding:0;background:#f8fafc;">
  <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;
              max-width:640px;margin:0 auto;padding:24px 16px;color:#0f172a;">
    <p style="color:#16a34a;font-size:12px;font-weight:600;letter-spacing:0.04em;margin:0 0 8px;">HUMUMU · 每日汇总</p>
    <h1 style="font-size:20px;margin:0 0 8px;">今日订阅更新{date_line}</h1>
    <p style="color:#64748b;font-size:14px;margin:0 0 16px;">共 <strong style="color:#0f172a;">{total}</strong> 篇新论文来自你的订阅：</p>
    <ul style="padding-left:18px;margin:0;">
    {lis}
    </ul>
    {extra}
    {footer}
  </div>
</body>
</html>"""


def _render_summary_text(
    articles: Sequence[dict[str, Any]],
    *,
    settings_href: str = "",
    date_label: str = "",
) -> str:
    total = len(articles)
    shown = list(articles[:_DIGEST_LIST_CAP])
    lines = [
        "Humumu · 每日汇总" + (f"（{date_label}）" if date_label else ""),
        f"共 {total} 篇新论文来自你的订阅：",
        "",
    ]
    for i, a in enumerate(shown, 1):
        jn = a.get("journal_name") or ""
        title = a.get("title") or "（无标题）"
        link = nc.article_link(a.get("url"), a.get("doi"))
        head = f"{i}. [{jn}] {title}" if jn else f"{i}. {title}"
        lines.append(head)
        if link:
            lines.append(f"   {link}")
    if total > len(shown):
        lines.append("")
        lines.append(f"还有 {total - len(shown)} 篇未列出，请登录 Humumu 查看。")
    if settings_href:
        lines.append("")
        lines.append(f"管理推送设置：{settings_href}")
    return "\n".join(lines)


class EmailNotifier:
    def __init__(self, settings: Settings) -> None:
        self.host = settings.smtp_host or ""
        self.port = settings.smtp_port
        self.user = settings.smtp_user or ""
        self.password = settings.smtp_pass or ""
        self.from_addr = settings.smtp_from or settings.smtp_user or ""
        self.public_app_url = getattr(settings, "public_app_url", "") or ""

    def is_configured(self) -> bool:
        return bool(self.host)

    def send_article(
        self,
        *,
        to_email: str,
        journal_name: str,
        title: str,
        authors: Sequence[str],
        abstract: str,
        url: str,
        doi: str,
        match_reasons: Sequence[str] | str | None = None,
        article_id: str | None = None,
    ) -> bool:
        """
        Send single-article email.

        Returns True if sent, False if skipped (not configured / no email).
        Raises on SMTP failure after an attempted send.
        """
        if not self.is_configured():
            logger.warning("email notifier: SMTP host empty; skip send")
            return False
        if not nc.is_real_email(to_email):
            logger.warning("email notifier: user has no real email; skip send")
            return False

        settings_href = nc.settings_url(self.public_app_url)
        app_href = nc.article_app_url(self.public_app_url, article_id)
        subject = nc.email_realtime_subject(journal_name, title)
        html_body = _render_article_html(
            journal_name=journal_name,
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            doi=doi or "",
            match_reasons=match_reasons,
            settings_href=settings_href,
            app_href=app_href,
        )
        text_body = _render_article_text(
            journal_name=journal_name,
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            doi=doi or "",
            match_reasons=match_reasons,
            settings_href=settings_href,
            app_href=app_href,
        )
        self._send_multipart(to_email, subject, text_body, html_body)
        logger.info("email sent to %s for article %s", to_email, doi or title)
        return True

    def send_summary(
        self,
        *,
        to_email: str,
        articles: Sequence[dict[str, Any]],
        date_label: str = "",
    ) -> bool:
        if not self.is_configured():
            logger.warning("email notifier: SMTP host empty; skip summary")
            return False
        if not nc.is_real_email(to_email):
            logger.warning("email notifier: user has no real email; skip summary")
            return False
        if not articles:
            return False

        settings_href = nc.settings_url(self.public_app_url)
        subject = nc.email_digest_subject(len(articles), date_label=date_label)
        html_body = _render_summary_html(
            articles, settings_href=settings_href, date_label=date_label
        )
        text_body = _render_summary_text(
            articles, settings_href=settings_href, date_label=date_label
        )
        self._send_multipart(to_email, subject, text_body, html_body)
        logger.info("email summary sent to %s (%d articles)", to_email, len(articles))
        return True

    def _send_multipart(
        self, to_email: str, subject: str, text_body: str, html_body: str
    ) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_addr
        msg["To"] = to_email
        msg["Subject"] = subject
        # plain first, html second (clients prefer the last part)
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(self.host, self.port, timeout=30) as server:
            try:
                server.starttls()
            except smtplib.SMTPException:
                # some servers don't support STARTTLS
                pass
            if self.user:
                server.login(self.user, self.password)
            server.sendmail(self.from_addr, [to_email], msg.as_string())
