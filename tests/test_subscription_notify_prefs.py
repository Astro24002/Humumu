"""ASGI tests for per-subscription notify preference PATCH."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.deps import get_current_user_id
from app.main import app
from app.schemas.subscription import JournalSubscriptionOut


class _EmptySession:
    async def execute(self, statement):  # noqa: ANN001
        raise RuntimeError("session should be mocked at service layer")

    async def commit(self) -> None:
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


@pytest.fixture
def authed_user_id():
    uid = str(uuid.uuid4())

    async def override_user_id():
        return uid

    app.dependency_overrides[get_current_user_id] = override_user_id
    return uid


def _sub_out(**overrides) -> JournalSubscriptionOut:
    base = {
        "user_id": str(uuid.uuid4()),
        "journal_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc),
        "push_frequency": "default",
        "email_enabled": True,
        "wechat_enabled": True,
    }
    base.update(overrides)
    return JournalSubscriptionOut(**base)


@pytest.mark.asyncio
async def test_patch_subscription_prefs_success(client, authed_user_id):
    jid = str(uuid.uuid4())
    row = MagicMock()
    row.user_id = uuid.UUID(authed_user_id)
    row.journal_id = uuid.UUID(jid)
    row.created_at = datetime.now(timezone.utc)
    row.push_frequency = "realtime"
    row.email_enabled = False
    row.wechat_enabled = True

    with (
        patch(
            "app.routers.subscriptions.sub_service.update_journal_subscription",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_upd,
        patch(
            "app.routers.subscriptions.sub_service.get_journal_subscription",
            new_callable=AsyncMock,
            return_value=row,
        ),
    ):
        r = await client.patch(
            f"/api/v1/subscriptions/journals/{jid}",
            json={
                "push_frequency": "realtime",
                "email_enabled": False,
                "wechat_enabled": True,
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["push_frequency"] == "realtime"
    assert body["email_enabled"] is False
    assert body["wechat_enabled"] is True
    mock_upd.assert_awaited_once()
    assert mock_upd.await_args.kwargs["push_frequency"] == "realtime"
    assert mock_upd.await_args.kwargs["email_enabled"] is False


@pytest.mark.asyncio
async def test_patch_subscription_prefs_empty_body_400(client, authed_user_id):
    jid = str(uuid.uuid4())
    r = await client.patch(f"/api/v1/subscriptions/journals/{jid}", json={})
    assert r.status_code == 400
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_patch_subscription_prefs_not_found(client, authed_user_id):
    jid = str(uuid.uuid4())
    with patch(
        "app.routers.subscriptions.sub_service.update_journal_subscription",
        new_callable=AsyncMock,
        return_value=False,
    ):
        r = await client.patch(
            f"/api/v1/subscriptions/journals/{jid}",
            json={"email_enabled": False},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_subscription_invalid_frequency(client, authed_user_id):
    jid = str(uuid.uuid4())
    with patch(
        "app.routers.subscriptions.sub_service.update_journal_subscription",
        new_callable=AsyncMock,
        side_effect=ValueError("push_frequency must be one of: default, realtime, daily"),
    ):
        r = await client.patch(
            f"/api/v1/subscriptions/journals/{jid}",
            json={"push_frequency": "weekly"},
        )
    assert r.status_code == 400
    assert "push_frequency" in r.json()["error"]


@pytest.mark.asyncio
async def test_patch_without_auth_401(client):
    jid = str(uuid.uuid4())
    r = await client.patch(
        f"/api/v1/subscriptions/journals/{jid}",
        json={"email_enabled": False},
    )
    assert r.status_code == 401
