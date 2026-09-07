"""ASGI tests for auth register/login with an in-memory fake user store."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import app
from app.services.password import hash_password, verify_password


class FakeUser:
    def __init__(
        self,
        email: str,
        password_hash: str,
        name: str = "",
        *,
        user_id: uuid.UUID | None = None,
    ):
        now = datetime.now(timezone.utc)
        self.id = user_id or uuid.uuid4()
        self.email = email
        self.password_hash = password_hash
        self.name = name or ""
        self.wechat_openid = None
        self.push_frequency = "daily"
        self.wechat_template_subscribed = False
        self.is_admin = False
        self.created_at = now
        self.updated_at = now


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    """Minimal async session stand-in used via dependency override."""

    def __init__(self, store: dict[str, FakeUser]):
        self.store = store
        self._pending: FakeUser | None = None

    async def execute(self, statement):  # noqa: ANN001
        # SQLAlchemy select(User).where(User.email == email)
        # Inspect compiled-ish where clause via string fallback on criterion.
        email = self._extract_email(statement)
        if email is None:
            return FakeResult(None)
        return FakeResult(self.store.get(email))

    def _extract_email(self, statement) -> str | None:  # noqa: ANN001
        try:
            wheres = list(statement._where_criteria)  # noqa: SLF001
        except Exception:
            return None
        for criterion in wheres:
            right = getattr(criterion, "right", None)
            if right is None:
                continue
            value = getattr(right, "value", None)
            if isinstance(value, str):
                return value
        return None

    def add(self, user) -> None:  # noqa: ANN001
        if getattr(user, "id", None) is None:
            user.id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        if getattr(user, "created_at", None) is None:
            user.created_at = now
        if getattr(user, "updated_at", None) is None:
            user.updated_at = now
        if getattr(user, "push_frequency", None) is None:
            user.push_frequency = "daily"
        if getattr(user, "wechat_template_subscribed", None) is None:
            user.wechat_template_subscribed = False
        if getattr(user, "wechat_openid", None) is None:
            user.wechat_openid = None
        if getattr(user, "name", None) is None:
            user.name = ""
        if getattr(user, "is_admin", None) is None:
            user.is_admin = False
        self._pending = user

    async def flush(self) -> None:
        if self._pending is not None:
            # Simulate unique email constraint
            if self._pending.email in self.store:
                from sqlalchemy.exc import IntegrityError

                raise IntegrityError("duplicate", params=None, orig=Exception("unique"))
            self.store[self._pending.email] = self._pending
            self._pending = None

    async def commit(self) -> None:
        await self.flush()

    async def refresh(self, user) -> None:  # noqa: ANN001
        return None

    async def rollback(self) -> None:
        self._pending = None


@pytest.fixture
def user_store() -> dict[str, FakeUser]:
    return {}


@pytest.fixture
async def client(user_store: dict[str, FakeUser]):
    async def override_get_session():
        yield FakeSession(user_store)

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_password_too_short_returns_400_with_error_key(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "12345", "name": "A"},
    )
    assert r.status_code == 400
    body = r.json()
    assert "error" in body
    assert "password" in body["error"].lower() or "6" in body["error"]


@pytest.mark.asyncio
async def test_register_success(client, user_store):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "secret1", "name": "New User"},
    )
    assert r.status_code == 201
    body = r.json()
    assert "token" in body and body["token"]
    assert body["has_email"] is True
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["name"] == "New User"
    assert body["user"]["is_admin"] is False
    assert "password_hash" not in body["user"]
    assert "new@example.com" in user_store
    assert verify_password("secret1", user_store["new@example.com"].password_hash)


@pytest.mark.asyncio
async def test_register_duplicate_email_409(client, user_store):
    user_store["dup@example.com"] = FakeUser(
        email="dup@example.com",
        password_hash=hash_password("secret1"),
        name="Existing",
    )
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "secret1", "name": "X"},
    )
    assert r.status_code == 409
    assert r.json() == {"error": "email already registered"}


@pytest.mark.asyncio
async def test_login_success(client, user_store):
    user_store["login@example.com"] = FakeUser(
        email="login@example.com",
        password_hash=hash_password("secret1"),
        name="Login",
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "secret1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["has_email"] is True
    assert body["user"]["email"] == "login@example.com"
    assert body["user"]["is_admin"] is False
    assert "password_hash" not in body["user"]


@pytest.mark.asyncio
async def test_login_returns_is_admin_true_for_admin(client, user_store):
    admin = FakeUser(
        email="admin@example.com",
        password_hash=hash_password("secret1"),
        name="Admin",
    )
    admin.is_admin = True
    user_store["admin@example.com"] = admin
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "secret1"},
    )
    assert r.status_code == 200
    assert r.json()["user"]["is_admin"] is True


@pytest.mark.asyncio
async def test_me_401_without_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_profile_with_is_admin(client):
    from unittest.mock import AsyncMock, patch

    from app.deps import get_current_user_id

    admin = FakeUser(
        email="admin@example.com",
        password_hash=hash_password("secret1"),
        name="Admin",
    )
    admin.is_admin = True
    uid = str(admin.id)

    async def override_uid():
        return uid

    app.dependency_overrides[get_current_user_id] = override_uid
    try:
        with patch(
            "app.routers.auth.user_service.get_by_id",
            new_callable=AsyncMock,
            return_value=admin,
        ):
            r = await client.get("/api/v1/auth/me")
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["email"] == "admin@example.com"
        assert body["user"]["is_admin"] is True
        assert body["has_email"] is True
        assert "token" not in body
        assert "password_hash" not in body["user"]
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_me_401_when_user_missing(client):
    from unittest.mock import AsyncMock, patch

    from app.deps import get_current_user_id

    async def override_uid():
        return str(uuid.uuid4())

    app.dependency_overrides[get_current_user_id] = override_uid
    try:
        with patch(
            "app.routers.auth.user_service.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_login_invalid_password_401(client, user_store):
    user_store["login@example.com"] = FakeUser(
        email="login@example.com",
        password_hash=hash_password("secret1"),
        name="Login",
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
    )
    assert r.status_code == 401
    assert r.json() == {"error": "invalid email or password"}


@pytest.mark.asyncio
async def test_login_missing_user_401(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "secret1"},
    )
    assert r.status_code == 401
    assert r.json() == {"error": "invalid email or password"}


@pytest.mark.asyncio
async def test_bind_email_success_for_wechat_stub(client):
    from unittest.mock import AsyncMock, patch

    from app.deps import get_current_user_id
    from app.services.password import verify_password

    openid = "ox_stub_bind"
    stub = FakeUser(
        email=f"{openid}@wechat.user",
        password_hash="",
        name="WeChat User",
    )
    stub.wechat_openid = openid
    uid = str(stub.id)

    async def override_uid():
        return uid

    bound = FakeUser(
        email="real@example.com",
        password_hash=hash_password("secret12"),
        name="WeChat User",
        user_id=stub.id,
    )
    bound.wechat_openid = openid

    app.dependency_overrides[get_current_user_id] = override_uid
    try:
        with (
            patch(
                "app.routers.auth.user_service.get_by_id",
                new_callable=AsyncMock,
                return_value=stub,
            ),
            patch(
                "app.routers.auth.user_service.get_by_email",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.routers.auth.user_service.bind_email",
                new_callable=AsyncMock,
                return_value=bound,
            ) as mock_bind,
        ):
            r = await client.post(
                "/api/v1/auth/bind-email",
                json={"email": "real@example.com", "password": "secret12"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["has_email"] is True
        assert body["user"]["email"] == "real@example.com"
        assert body["token"]
        mock_bind.assert_awaited_once()
        kwargs = mock_bind.await_args.kwargs
        assert kwargs["email"] == "real@example.com"
        assert verify_password("secret12", kwargs["password_hash"])
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_bind_email_409_when_already_has_email(client):
    from unittest.mock import AsyncMock, patch

    from app.deps import get_current_user_id

    user = FakeUser(
        email="already@example.com",
        password_hash=hash_password("secret1"),
        name="Has Email",
    )
    uid = str(user.id)

    async def override_uid():
        return uid

    app.dependency_overrides[get_current_user_id] = override_uid
    try:
        with patch(
            "app.routers.auth.user_service.get_by_id",
            new_callable=AsyncMock,
            return_value=user,
        ):
            r = await client.post(
                "/api/v1/auth/bind-email",
                json={"email": "other@example.com", "password": "secret12"},
            )
        assert r.status_code == 409
        assert r.json() == {"error": "email already bound"}
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_bind_email_409_when_email_taken(client):
    from unittest.mock import AsyncMock, patch

    from app.deps import get_current_user_id

    openid = "ox_stub_taken"
    stub = FakeUser(
        email=f"{openid}@wechat.user",
        password_hash="",
        name="WeChat User",
    )
    stub.wechat_openid = openid
    other = FakeUser(
        email="taken@example.com",
        password_hash=hash_password("secret1"),
        name="Other",
    )
    uid = str(stub.id)

    async def override_uid():
        return uid

    app.dependency_overrides[get_current_user_id] = override_uid
    try:
        with (
            patch(
                "app.routers.auth.user_service.get_by_id",
                new_callable=AsyncMock,
                return_value=stub,
            ),
            patch(
                "app.routers.auth.user_service.get_by_email",
                new_callable=AsyncMock,
                return_value=other,
            ),
        ):
            r = await client.post(
                "/api/v1/auth/bind-email",
                json={"email": "taken@example.com", "password": "secret12"},
            )
        assert r.status_code == 409
        assert r.json() == {"error": "email already registered"}
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_bind_email_401_without_token(client):
    r = await client.post(
        "/api/v1/auth/bind-email",
        json={"email": "x@example.com", "password": "secret12"},
    )
    assert r.status_code == 401
