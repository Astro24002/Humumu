"""WeChat mini-program API helpers (jscode2session)."""

from __future__ import annotations

import httpx

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WeChatAPIError(Exception):
    """Raised when WeChat jscode2session fails."""


async def code_to_openid(appid: str, secret: str, code: str) -> str:
    """Exchange a mini-program login code for openid via jscode2session."""
    if not appid or not secret:
        raise WeChatAPIError("wechat appid or secret not configured")
    if not code:
        raise WeChatAPIError("empty code")

    params = {
        "appid": appid,
        "secret": secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(JSCODE2SESSION_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except WeChatAPIError:
        raise
    except Exception as exc:
        raise WeChatAPIError(f"wechat jscode2session request failed: {exc}") from exc

    errcode = data.get("errcode") or 0
    if errcode != 0:
        raise WeChatAPIError(
            f"wechat jscode2session error: {errcode} {data.get('errmsg', '')}"
        )

    openid = data.get("openid") or ""
    if not openid:
        raise WeChatAPIError("wechat jscode2session returned empty openid")
    return openid
