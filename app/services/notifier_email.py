"""SMTP email notifier. Skips cleanly when SMTP host is empty."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Sequence

from app.config import Settings

logger = logging.getLogger(__name__)


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _render_article_html(
    *,
    journal_name: str,
    title: str,
    authors: Sequence[str],
    abstract: str,
    url: str,
    doi: str,
) -> str:
    authors_display = ", ".join(authors or [])
    return f"""<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #2c3e50;">{journal_name}</h2>
    <h3>{title}</h3>
    <p style="color: #7f8c8d;">{authors_display}</p>
    <hr>
    <p>{abstract}</p>
    <p>
        <a href="{url}" style="background: #3498db; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">Read Full Article</a>
        &nbsp; DOI: {doi}
    </p>
</body>
</html>"""


def _render_summary_html(articles: Sequence[dict[str, Any]]) -> str:
    items = []
    for a in articles:
        jn = a.get("journal_name") or ""
        title = a.get("title") or ""
        url = a.get("url") or "#"
        items.append(f'<li><strong>{jn}</strong>: <a href="{url}">{title}</a></li>')
    lis = "\n".join(items)
    return f"""<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2>Daily article summary</h2>
    <p>{len(articles)} new article(s) from your subscriptions:</p>
    <ul>
    {lis}
    </ul>
</body>
</html>"""


class EmailNotifier:
    def __init__(self, settings: Settings) -> None:
        self.host = settings.smtp_host or ""
        self.port = settings.smtp_port
        self.user = settings.smtp_user or ""
        self.password = settings.smtp_pass or ""
        self.from_addr = settings.smtp_from or settings.smtp_user or ""

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
    ) -> bool:
        """
        Send single-article email.

        Returns True if sent, False if skipped (not configured / no email).
        Raises on SMTP failure after an attempted send.
        """
        if not self.is_configured():
            logger.warning("email notifier: SMTP host empty; skip send")
            return False
        if not to_email:
            logger.warning("email notifier: user has no email; skip send")
            return False

        subject = f"[{journal_name}] {_truncate(title, 80)}"
        body = _render_article_html(
            journal_name=journal_name,
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            doi=doi or "",
        )
        self._send_html(to_email, subject, body)
        logger.info("email sent to %s for article %s", to_email, doi or title)
        return True

    def send_summary(
        self,
        *,
        to_email: str,
        articles: Sequence[dict[str, Any]],
    ) -> bool:
        if not self.is_configured():
            logger.warning("email notifier: SMTP host empty; skip summary")
            return False
        if not to_email:
            logger.warning("email notifier: user has no email; skip summary")
            return False
        if not articles:
            return False

        subject = f"Daily summary: {len(articles)} new article(s)"
        body = _render_summary_html(articles)
        self._send_html(to_email, subject, body)
        logger.info("email summary sent to %s (%d articles)", to_email, len(articles))
        return True

    def _send_html(self, to_email: str, subject: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_addr
        msg["To"] = to_email
        msg["Subject"] = subject
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
