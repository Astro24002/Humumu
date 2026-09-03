"""ASGI tests for admin APIs (no live Postgres)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.deps import get_current_user_id, require_admin
from app.main import app
from app.schemas.journal import JournalOut, JournalRequestOut


class _EmptySession:
    """Session stand-in; services are patched so execute is unused."""

    async def execute(self, statement):  # noqa: ANN001
        raise AssertionError("session.execute should not be called when services are mocked")

    async def commit(self) -> None:
        return None


def _sample_journal(**overrides) -> JournalOut:
    data = {
        "id": str(uuid.uuid4()),
        "name": "Nature",
        "slug": "nature",
        "source_type": "rss",
        "source_url": "https://example.com/nature.rss",
        "description": "Science journal",
        "fetch_interval": 1800,
        "is_active": True,
        "created_by": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "article_count": 3,
        "last_article_date": datetime(2026, 6, 1, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return JournalOut.model_validate(data)


def _sample_request(**overrides) -> JournalRequestOut:
    data = {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "journal_name": "Wanted Journal",
        "source_url": "https://example.com/wanted.rss",
        "status": "pending",
        "created_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "reviewed_at": None,
    }
    data.update(overrides)
    return JournalRequestOut.model_validate(data)


def _sample_user(**overrides):
    data = {
        "id": str(uuid.uuid4()),
        "email": "admin@example.com",
        "name": "Admin",
        "password_hash": "should-not-leak",
        "push_frequency": "realtime",
        "wechat_openid": None,
        "wechat_template_subscribed": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


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
    user_id = str(uuid.uuid4())

    async def override_user_id():
        return user_id

    async def override_admin():
        return user_id

    app.dependency_overrides[get_current_user_id] = override_user_id
    app.dependency_overrides[require_admin] = override_admin
    yield user_id
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_admin_stats_shape(client, authed_user_id):
    with (
        patch(
            "app.routers.admin.journal_service.count_journals",
            new_callable=AsyncMock,
            return_value=2,
        ),
        patch(
            "app.routers.admin.article_service.count_articles",
            new_callable=AsyncMock,
            return_value=10,
        ),
        patch(
            "app.routers.admin.user_service.count_users",
            new_callable=AsyncMock,
            return_value=5,
        ),
        patch(
            "app.routers.admin.journal_service.count_pending_requests",
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):
        r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 200
    assert r.json() == {
        "journal_count": 2,
        "article_count": 10,
        "user_count": 5,
        "pending_requests": 1,
    }


@pytest.mark.asyncio
async def test_admin_list_journals(client, authed_user_id):
    j = _sample_journal()
    with patch(
        "app.routers.admin.journal_service.list_journals",
        new_callable=AsyncMock,
        return_value=[j],
    ):
        r = await client.get("/api/v1/admin/journals")
    assert r.status_code == 200
    body = r.json()
    assert "journals" in body
    assert body["journals"][0]["name"] == "Nature"
    assert body["journals"][0]["article_count"] == 3


@pytest.mark.asyncio
async def test_admin_create_journal_201_bare(client, authed_user_id):
    j = _sample_journal(name="Science", slug="science", fetch_interval=3600)
    with patch(
        "app.routers.admin.journal_service.create_journal",
        new_callable=AsyncMock,
        return_value=j,
    ) as mock_create:
        r = await client.post(
            "/api/v1/admin/journals",
            json={
                "name": "Science",
                "source_url": "https://example.com/science.rss",
                "fetch_interval": 3600,
            },
        )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == j.id
    assert body["name"] == "Science"
    assert "journals" not in body
    mock_create.assert_awaited_once()
    kwargs = mock_create.await_args.kwargs
    assert kwargs["name"] == "Science"
    assert kwargs["fetch_interval"].total_seconds() == 3600
    assert kwargs["slug"] is None  # omitted → service slugifies


@pytest.mark.asyncio
async def test_admin_update_journal_message(client, authed_user_id):
    jid = str(uuid.uuid4())
    with patch(
        "app.routers.admin.journal_service.update_journal",
        new_callable=AsyncMock,
        return_value=True,
    ):
        r = await client.put(f"/api/v1/admin/journals/{jid}", json={"name": "Renamed"})
    assert r.status_code == 200
    assert r.json() == {"message": "updated"}


@pytest.mark.asyncio
async def test_admin_delete_journal_message(client, authed_user_id):
    jid = str(uuid.uuid4())
    with patch(
        "app.routers.admin.journal_service.delete_journal",
        new_callable=AsyncMock,
        return_value=True,
    ):
        r = await client.delete(f"/api/v1/admin/journals/{jid}")
    assert r.status_code == 200
    assert r.json() == {"message": "deleted"}


@pytest.mark.asyncio
async def test_admin_list_requests(client, authed_user_id):
    req = _sample_request()
    with patch(
        "app.routers.admin.journal_service.list_all_journal_requests",
        new_callable=AsyncMock,
        return_value=[req],
    ):
        r = await client.get("/api/v1/admin/requests")
    assert r.status_code == 200
    body = r.json()
    assert "requests" in body
    assert body["requests"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_admin_review_request_approved(client, authed_user_id):
    rid = str(uuid.uuid4())
    with patch(
        "app.routers.admin.journal_service.update_request_status",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_upd:
        r = await client.put(f"/api/v1/admin/requests/{rid}", json={"status": "approved"})
    assert r.status_code == 200
    assert r.json() == {"message": "request approved"}
    mock_upd.assert_awaited_once()
    assert mock_upd.await_args.args[1] == rid
    assert mock_upd.await_args.args[2] == "approved"


@pytest.mark.asyncio
async def test_admin_review_invalid_status_400(client, authed_user_id):
    rid = str(uuid.uuid4())
    r = await client.put(f"/api/v1/admin/requests/{rid}", json={"status": "pending"})
    assert r.status_code == 400
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_admin_users_omit_password_hash(client, authed_user_id):
    user = _sample_user()
    with patch(
        "app.routers.admin.user_service.list_all_users",
        new_callable=AsyncMock,
        return_value=[user],
    ):
        r = await client.get("/api/v1/admin/users")
    assert r.status_code == 200
    body = r.json()
    assert "users" in body
    assert len(body["users"]) == 1
    u = body["users"][0]
    assert u["email"] == "admin@example.com"
    assert u["name"] == "Admin"
    assert "password_hash" not in u
    assert "password" not in u


@pytest.mark.asyncio
async def test_admin_without_auth_401(client):
    r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 401
    assert "error" in r.json()

    r = await client.get("/api/v1/admin/users")
    assert r.status_code == 401

    r = await client.post(
        "/api/v1/admin/journals",
        json={"name": "X", "source_url": "https://example.com/x"},
    )
    assert r.status_code == 401
