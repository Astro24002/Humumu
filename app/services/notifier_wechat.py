"""WeChat subscribe-message notifier with simple access_token cache."""

from __future__ import annotations

import logging
import time
from typing import Any, Sequence

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send"


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


class WeChatNotifier:
    def __init__(self, settings: Settings) -> None:
        self.appid = settings.wechat_appid or ""
        self.secret = settings.wechat_secret or ""
        self.template_realtime = settings.wechat_template_realtime or ""
        self.template_daily = settings.wechat_template_daily or ""
        self._token: str = ""
        self._token_expiry: float = 0.0

    def is_configured(self) -> bool:
        return bool(self.appid and self.secret)

    async def send_article(
        self,
        *,
        openid: str,
        journal_name: str,
        title: str,
        authors: Sequence[str],
        abstract: str,
        doi: str,
    ) -> bool:
        """
        Send realtime template message.

        Returns True if sent, False if skipped (not configured / no openid).
        Raises on API failure after an attempted send.
        """
        if not self.is_configured() or not self.template_realtime:
            logger.warning("wechat notifier: appid/template missing; skip send")
            return False
        if not openid:
            logger.warning("wechat notifier: user has no openid; skip send")
            return False

        token = await self._get_access_token()
        data = {
            "journal": {"value": journal_name, "color": "#2c3e50"},
            "title": {"value": _truncate(title, 100), "color": "#000000"},
            "authors": {
                "value": _truncate(", ".join(authors or []), 80),
                "color": "#7f8c8d",
            },
            "abstract": {"value": _truncate(abstract or "", 200), "color": "#666666"},
            "doi": {"value": doi or "", "color": "#3498db"},
        }
        await self._post_template(token, openid, self.template_realtime, data)
        logger.info("wechat message sent to %s for article %s", openid, doi or title)
        return True

    async def send_summary(
        self,
        *,
        openid: str,
        articles: Sequence[dict[str, Any]],
    ) -> bool:
        if not self.is_configured() or not self.template_daily:
            logger.warning("wechat notifier: appid/daily template missing; skip summary")
            return False
        if not openid:
            logger.warning("wechat notifier: user has no openid; skip summary")
            return False
        if not articles:
            return False

        lines: list[str] = []
        for i, a in enumerate(articles):
            if i >= 5:
                lines.append(f"...还有 {len(articles) - 5} 篇")
                break
            jn = a.get("journal_name") or ""
            title = _truncate(a.get("title") or "", 60)
            lines.append(f"《{jn}》— {title}")

        from datetime import date

        token = await self._get_access_token()
        data = {
            "date": {"value": date.today().isoformat(), "color": "#2c3e50"},
            "summary": {"value": "\n".join(lines), "color": "#000000"},
            "count": {"value": f"{len(articles)} 篇", "color": "#3498db"},
        }
        await self._post_template(token, openid, self.template_daily, data)
        logger.info("wechat summary sent to %s (%d articles)", openid, len(articles))
        return True

    async def _get_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry:
            return self._token

        params = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.secret,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_TOKEN_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()

        token = payload.get("access_token") or ""
        if not token:
            raise RuntimeError(
                f"failed to get wechat access token: {payload.get('errmsg', payload)}"
            )
        expires_in = int(payload.get("expires_in") or 7200)
        # cache slightly under lifetime
        self._token = token
        self._token_expiry = now + max(expires_in - 60, 60)
        return token

    async def _post_template(
        self,
        token: str,
        openid: str,
        template_id: str,
        data: dict[str, Any],
    ) -> None:
        url = f"{_SEND_URL}?access_token={token}"
        body = {
            "touser": openid,
            "template_id": template_id,
            "data": data,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            result = resp.json()

        errcode = result.get("errcode") or 0
        if errcode != 0:
            raise RuntimeError(
                f"wechat api error: {errcode} {result.get('errmsg', '')}"
            )
