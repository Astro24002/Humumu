"""ASGI tests for WeChat login, bind-account, and template settings."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.db import get_session
from app.deps import get_current_user_id
from app.main import app
from app.services.password import hash_password
from app.services.wechat_api import WeChatAPIError


class FakeUser:
    def __init__(
        self,
        email: str,
        password_hash: str = "",
        name: str = "",
        *,
        user_id: uuid.UUID | None = None,
        wechat_openid: str | None = None,
        wechat_template_subscribed: bool = False,
        push_frequency: str = "daily",
    ):
        now = datetime.now(timezone.utc)
        self.id = user_id or uuid.uuid4()
        self.email = email
        self.password_hash = password_hash
        self.name = name or ""
        self.wechat_openid = wechat_openid
        self.push_frequency = push_frequency
        self.wechat_template_subscribed = wechat_template_subscribed
        self.is_admin = False
        self.created_at = now
        self.updated_at = now


class _EmptySession:
    async def execute(self, statement):  # noqa: ANN001
        raise AssertionError("session.execute should not be called when services are mocked")

    async def commit(self) -> None:
        return None

    async def refresh(self, obj) -> None:  # noqa: ANN001
        return None

    async def rollback(self) -> None:
        return None


@pytest.fixture
async def client():
    async def override_get_session():
        yield _EmptySession()

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def authed_user_id():
    user_id = str(uuid.uuid4())

    async def override_user_id():
        return user_id

    app.dependency_overrides[get_current_user_id] = override_user_id
    yield user_id
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture
def wechat_settings(monkeypatch):
    monkeypatch.setenv("WECHAT_APPID", "test-appid")
    monkeypatch.setenv("WECHAT_SECRET", "test-secret")
    monkeypatch.setenv("WECHAT_TEMPLATE_REALTIME", "tpl-realtime")
    monkeypatch.setenv("WECHAT_TEMPLATE_DAILY", "tpl-daily")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_wechat_login_new_user_has_email_false(client, wechat_settings):
    openid = "ox_new_user_abc"
    created = FakeUser(
        email=f"{openid}@wechat.user",
        password_hash="",
        name="WeChat User",
        wechat_openid=openid,
    )

    with (
        patch(
            "app.routers.auth.code_to_openid",
            new_callable=AsyncMock,
            return_value=openid,
        ),
        patch(
            "app.routers.auth.user_service.get_by_wechat_openid",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.routers.auth.user_service.create_user",
            new_callable=AsyncMock,
            return_value=created,
        ) as mock_create,
    ):
        r = await client.post("/api/v1/auth/wechat", json={"code": "wx-code-1"})

    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["has_email"] is False
    assert body["user"]["email"].endswith("@wechat.user")
    assert body["user"]["email"] == f"{openid}@wechat.user"
    assert body["user"]["name"] == "WeChat User"
    assert body["user"]["wechat_openid"] == openid
    mock_create.assert_awaited_once()
    kwargs = mock_create.await_args.kwargs
    assert kwargs["email"] == f"{openid}@wechat.user"
    assert kwargs["password_hash"] == ""
    assert kwargs["wechat_openid"] == openid
    assert kwargs["push_frequency"] == "daily"


@pytest.mark.asyncio
async def test_wechat_login_existing_user(client, wechat_settings):
    openid = "ox_existing"
    existing = FakeUser(
        email="real@example.com",
        password_hash=hash_password("secret1"),
        name="Bound User",
        wechat_openid=openid,
    )

    with (
        patch(
            "app.routers.auth.code_to_openid",
            new_callable=AsyncMock,
            return_value=openid,
        ),
        patch(
            "app.routers.auth.user_service.get_by_wechat_openid",
            new_callable=AsyncMock,
            return_value=existing,
        ),
        patch(
            "app.routers.auth.user_service.create_user",
            new_callable=AsyncMock,
        ) as mock_create,
    ):
        r = await client.post("/api/v1/auth/wechat", json={"code": "wx-code-2"})

    assert r.status_code == 200
    body = r.json()
    assert body["has_email"] is True
    assert body["user"]["email"] == "real@example.com"
    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_wechat_login_api_fail_502(client, wechat_settings):
    with patch(
        "app.routers.auth.code_to_openid",
        new_callable=AsyncMock,
        side_effect=WeChatAPIError("boom"),
    ):
        r = await client.post("/api/v1/auth/wechat", json={"code": "bad-code"})

    assert r.status_code == 502
    assert r.json() == {"error": "wechat login failed"}


@pytest.mark.asyncio
async def test_bind_account_success(client, wechat_settings):
    openid = "ox_bind"
    user = FakeUser(
        email="bind@example.com",
        password_hash=hash_password("secret1"),
        name="Bind Me",
    )
    linked = FakeUser(
        email="bind@example.com",
        password_hash=user.password_hash,
        name="Bind Me",
        user_id=user.id,
        wechat_openid=openid,
    )

    with (
        patch(
            "app.routers.auth.code_to_openid",
            new_callable=AsyncMock,
            return_value=openid,
        ),
        patch(
            "app.routers.auth.user_service.get_by_email",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.routers.auth.user_service.get_by_wechat_openid",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.routers.auth.user_service.link_wechat",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_link,
        patch(
            "app.routers.auth.user_service.get_by_id",
            new_callable=AsyncMock,
            return_value=linked,
        ),
    ):
        r = await client.post(
            "/api/v1/auth/bind-account",
            json={"code": "wx-bind", "email": "bind@example.com", "password": "secret1"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["has_email"] is True
    assert body["user"]["wechat_openid"] == openid
    assert body["user"]["email"] == "bind@example.com"
    mock_link.assert_awaited_once()


@pytest.mark.asyncio
async def test_bind_account_invalid_password_401(client, wechat_settings):
    openid = "ox_bind_bad"
    user = FakeUser(
        email="bind@example.com",
        password_hash=hash_password("secret1"),
        name="Bind Me",
    )

    with (
        patch(
            "app.routers.auth.code_to_openid",
            new_callable=AsyncMock,
            return_value=openid,
        ),
        patch(
            "app.routers.auth.user_service.get_by_email",
            new_callable=AsyncMock,
            return_value=user,
        ),
    ):
        r = await client.post(
            "/api/v1/auth/bind-account",
            json={"code": "wx-bind", "email": "bind@example.com", "password": "wrong-password"},
        )

    assert r.status_code == 401
    assert r.json() == {"error": "invalid email or password"}


@pytest.mark.asyncio
async def test_bind_account_wechat_fail_502(client, wechat_settings):
    with patch(
        "app.routers.auth.code_to_openid",
        new_callable=AsyncMock,
        side_effect=WeChatAPIError("nope"),
    ):
        r = await client.post(
            "/api/v1/auth/bind-account",
            json={"code": "bad", "email": "a@example.com", "password": "secret1"},
        )

    assert r.status_code == 502
    assert r.json() == {"error": "wechat login failed"}


@pytest.mark.asyncio
async def test_bind_account_openid_taken_409(client, wechat_settings):
    openid = "ox_taken"
    target = FakeUser(
        email="bind@example.com",
        password_hash=hash_password("secret1"),
        name="Bind Me",
    )
    other = FakeUser(
        email="other@example.com",
        password_hash=hash_password("secret1"),
        name="Other",
        wechat_openid=openid,
    )
    with (
        patch(
            "app.routers.auth.code_to_openid",
            new_callable=AsyncMock,
            return_value=openid,
        ),
        patch(
            "app.routers.auth.user_service.get_by_email",
            new_callable=AsyncMock,
            return_value=target,
        ),
        patch(
            "app.routers.auth.user_service.get_by_wechat_openid",
            new_callable=AsyncMock,
            return_value=other,
        ),
        patch(
            "app.routers.auth.user_service.link_wechat",
            new_callable=AsyncMock,
        ) as mock_link,
    ):
        r = await client.post(
            "/api/v1/auth/bind-account",
            json={"code": "wx-bind", "email": "bind@example.com", "password": "secret1"},
        )
    assert r.status_code == 409
    assert r.json() == {"error": "wechat already bound to another account"}
    mock_link.assert_not_awaited()


@pytest.mark.asyncio
async def test_bind_account_already_linked_idempotent(client, wechat_settings):
    openid = "ox_same"
    user = FakeUser(
        email="bind@example.com",
        password_hash=hash_password("secret1"),
        name="Bind Me",
        wechat_openid=openid,
    )
    with (
        patch(
            "app.routers.auth.code_to_openid",
            new_callable=AsyncMock,
            return_value=openid,
        ),
        patch(
            "app.routers.auth.user_service.get_by_email",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.routers.auth.user_service.get_by_wechat_openid",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.routers.auth.user_service.link_wechat",
            new_callable=AsyncMock,
        ) as mock_link,
    ):
        r = await client.post(
            "/api/v1/auth/bind-account",
            json={"code": "wx-bind", "email": "bind@example.com", "password": "secret1"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["has_email"] is True
    assert body["user"]["wechat_openid"] == openid
    mock_link.assert_not_awaited()


@pytest.mark.asyncio
async def test_template_ids_filters_empties(client, authed_user_id, monkeypatch):
    monkeypatch.setenv("WECHAT_TEMPLATE_REALTIME", "tpl-rt")
    monkeypatch.setenv("WECHAT_TEMPLATE_DAILY", "")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    get_settings.cache_clear()

    r = await client.get("/api/v1/wechat/template-ids")
    assert r.status_code == 200
    assert r.json() == {"template_ids": ["tpl-rt"]}

    monkeypatch.setenv("WECHAT_TEMPLATE_REALTIME", "")
    monkeypatch.setenv("WECHAT_TEMPLATE_DAILY", "tpl-daily")
    get_settings.cache_clear()
    r = await client.get("/api/v1/wechat/template-ids")
    assert r.status_code == 200
    assert r.json() == {"template_ids": ["tpl-daily"]}

    monkeypatch.setenv("WECHAT_TEMPLATE_REALTIME", "a")
    monkeypatch.setenv("WECHAT_TEMPLATE_DAILY", "b")
    get_settings.cache_clear()
    r = await client.get("/api/v1/wechat/template-ids")
    assert r.status_code == 200
    assert r.json() == {"template_ids": ["a", "b"]}


@pytest.mark.asyncio
async def test_template_ids_requires_auth(client):
    r = await client.get("/api/v1/wechat/template-ids")
    assert r.status_code == 401
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_template_setting_get_put(client, authed_user_id):
    with patch(
        "app.routers.wechat.user_service.get_template_setting",
        new_callable=AsyncMock,
        return_value=False,
    ) as mock_get:
        r = await client.get("/api/v1/wechat/template-setting")
    assert r.status_code == 200
    assert r.json() == {"subscribed": False}
    mock_get.assert_awaited_once()
    assert mock_get.await_args.args[1] == authed_user_id

    with patch(
        "app.routers.wechat.user_service.update_template_setting",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_put:
        r = await client.put(
            "/api/v1/wechat/template-setting",
            json={"subscribed": True},
        )
    assert r.status_code == 200
    assert r.json() == {"subscribed": True}
    mock_put.assert_awaited_once()
    assert mock_put.await_args.args[1] == authed_user_id
    assert mock_put.await_args.args[2] is True


@pytest.mark.asyncio
async def test_code_to_openid_httpx_mocked():
    """Unit-level: code_to_openid parses jscode2session JSON via mocked httpx."""
    from app.services.wechat_api import code_to_openid

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"openid": "ox_from_httpx", "session_key": "sk", "errcode": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None):  # noqa: ANN001
            assert "jscode2session" in url
            assert params["appid"] == "aid"
            assert params["secret"] == "sec"
            assert params["js_code"] == "code1"
            assert params["grant_type"] == "authorization_code"
            return FakeResp()

    with patch("app.services.wechat_api.httpx.AsyncClient", FakeClient):
        openid = await code_to_openid("aid", "sec", "code1")
    assert openid == "ox_from_httpx"


@pytest.mark.asyncio
async def test_code_to_openid_errcode_raises():
    from app.services.wechat_api import code_to_openid

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"errcode": 40029, "errmsg": "invalid code"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None):  # noqa: ANN001
            return FakeResp()

    with patch("app.services.wechat_api.httpx.AsyncClient", FakeClient):
        with pytest.raises(WeChatAPIError):
            await code_to_openid("aid", "sec", "bad")


@pytest.mark.asyncio
async def test_code_to_openid_missing_config():
    from app.services.wechat_api import code_to_openid

    with pytest.raises(WeChatAPIError):
        await code_to_openid("", "sec", "code")
    with pytest.raises(WeChatAPIError):
        await code_to_openid("aid", "", "code")
    with pytest.raises(WeChatAPIError):
        await code_to_openid("aid", "sec", "")
