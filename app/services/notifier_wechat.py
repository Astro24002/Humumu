"""WeChat subscribe-message notifier with simple access_token cache."""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Sequence

import httpx

from app.config import Settings
from app.services import notify_content as nc

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send"

# Conservative thing.DATA lengths for common MP templates
_THING_SHORT = 20
_THING_MED = 40
_THING_LONG = 80


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
        url: str = "",
        match_reasons: Sequence[str] | str | None = None,
        article_id: str | None = None,
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
        authors_s = nc.format_authors(authors, max_n=2)
        abs_clean = nc.clean_abstract(abstract)
        reasons = nc.format_reasons(match_reasons)
        # Prefer DOI; else short reason; else dash — keeps required slots non-empty
        doi_or_meta = (doi or "").strip() or (f"匹配:{reasons}" if reasons else "")
        link = nc.article_link(url, doi)

        # Field keys must match the MP subscribe template configuration.
        # Values always non-empty to reduce WeChat API rejects on required slots.
        data = {
            "journal": nc.wechat_thing(
                journal_name or "期刊", empty="期刊", max_len=_THING_MED
            ),
            "title": nc.wechat_thing(
                title or "新论文", empty="新论文", max_len=_THING_LONG
            ),
            "authors": nc.wechat_thing(
                authors_s or "作者未标注", empty="作者未标注", max_len=_THING_MED
            ),
            "abstract": nc.wechat_thing(
                abs_clean or reasons or "打开查看详情",
                empty="打开查看详情",
                max_len=_THING_LONG,
            ),
            "doi": nc.wechat_thing(
                doi_or_meta or (link[:_THING_MED] if link else "—"),
                empty="—",
                max_len=_THING_MED,
            ),
        }
        page = nc.wechat_article_page(article_id)
        await self._post_template(
            token, openid, self.template_realtime, data, page=page
        )
        logger.info("wechat message sent to %s for article %s", openid, doi or title)
        return True

    async def send_summary(
        self,
        *,
        openid: str,
        articles: Sequence[dict[str, Any]],
        date_label: str = "",
    ) -> bool:
        if not self.is_configured() or not self.template_daily:
            logger.warning("wechat notifier: appid/daily template missing; skip summary")
            return False
        if not openid:
            logger.warning("wechat notifier: user has no openid; skip summary")
            return False
        if not articles:
            return False

        # Keep summary within typical thing length: top titles only.
        lines: list[str] = []
        budget = _THING_LONG
        for i, a in enumerate(articles):
            jn = (a.get("journal_name") or "").strip()
            title = nc.truncate(a.get("title") or "", 28)
            piece = f"{jn}·{title}" if jn else title
            piece = nc.truncate(piece, 36)
            if i == 0:
                candidate = piece
            else:
                candidate = "；".join(lines + [piece])
            if len(candidate) > budget and lines:
                lines.append(f"等{len(articles)}篇")
                break
            lines.append(piece)
            if i >= 2:
                if len(articles) > i + 1:
                    lines.append(f"等{len(articles)}篇")
                break

        summary = "；".join(lines) if lines else f"{len(articles)} 篇新论文"
        summary = nc.truncate(summary, budget)

        day = date_label or date.today().isoformat()
        token = await self._get_access_token()
        data = {
            "date": nc.wechat_thing(day, empty=date.today().isoformat(), max_len=16),
            "summary": nc.wechat_thing(summary, empty="订阅更新", max_len=_THING_LONG),
            "count": nc.wechat_thing(
                f"{len(articles)}篇", empty="0篇", max_len=8
            ),
        }
        await self._post_template(
            token,
            openid,
            self.template_daily,
            data,
            page=nc.wechat_digest_page(),
        )
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
        *,
        page: str | None = None,
    ) -> None:
        url = f"{_SEND_URL}?access_token={token}"
        body: dict[str, Any] = {
            "touser": openid,
            "template_id": template_id,
            "data": data,
            # formal env; trial/developer can be set via WeChat console when debugging
            "miniprogram_state": "formal",
            "lang": "zh_CN",
        }
        if page:
            body["page"] = page
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            result = resp.json()

        errcode = result.get("errcode") or 0
        if errcode != 0:
            raise RuntimeError(
                f"wechat api error: {errcode} {result.get('errmsg', '')}"
            )
