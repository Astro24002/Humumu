"""ASGI tests for My Updates feed API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.deps import get_current_user_id
from app.main import app


class _EmptySession:
    async def execute(self, statement):  # noqa: ANN001
        raise AssertionError("session.execute should not be called when services are mocked")

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


@pytest.mark.asyncio
async def test_my_updates_shape(client, authed_user_id):
    aid = str(uuid.uuid4())
    jid = str(uuid.uuid4())
    row = {
        "article_id": aid,
        "title": "Quantum widgets",
        "authors": ["Alice"],
        "abstract": "abs",
        "doi": "10.1/x",
        "url": "https://example.com/a",
        "original_url": "https://example.com/a",
        "publish_date": "2026-01-01",
        "fetched_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "journal_id": jid,
        "journal_name": "Nature",
        "content_type": "journal",
        "reasons": ["journal", "keyword"],
        "status": {
            "is_read": False,
            "is_starred": True,
            "is_later": False,
            "original_clicked_at": None,
        },
    }
    with patch(
        "app.routers.my_updates.updates_service.list_my_updates",
        new_callable=AsyncMock,
        return_value=[row],
    ) as mock_list:
        r = await client.get("/api/v1/my/updates?limit=10&filter=starred")
    assert r.status_code == 200
    body = r.json()
    assert "updates" in body
    item = body["updates"][0]
    assert item["title"] == "Quantum widgets"
    assert item["reasons"] == ["journal", "keyword"]
    assert item["status"]["is_starred"] is True
    assert item["original_url"] == "https://example.com/a"
    assert mock_list.await_args.kwargs["filter_name"] == "starred"
    assert mock_list.await_args.kwargs["limit"] == 10


@pytest.mark.asyncio
async def test_my_updates_empty(client, authed_user_id):
    with patch(
        "app.routers.my_updates.updates_service.list_my_updates",
        new_callable=AsyncMock,
        return_value=[],
    ):
        r = await client.get("/api/v1/my/updates")
    assert r.status_code == 200
    assert r.json() == {"updates": []}


@pytest.mark.asyncio
async def test_my_updates_without_auth_401(client):
    r = await client.get("/api/v1/my/updates")
    assert r.status_code == 401
