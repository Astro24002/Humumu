"""ASGI tests for reading status APIs (no live Postgres)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.deps import get_current_user_id
from app.main import app
from app.schemas.reading import ArticleStatusOut


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


def _sample_status(**overrides) -> ArticleStatusOut:
    base = {
        "user_id": str(uuid.uuid4()),
        "article_id": str(uuid.uuid4()),
        "is_read": False,
        "is_starred": False,
        "is_later": False,
        "original_clicked_at": None,
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return ArticleStatusOut(**base)


@pytest.mark.asyncio
async def test_get_status_default_when_missing(client, authed_user_id):
    aid = str(uuid.uuid4())
    with patch(
        "app.routers.reading.reading_service.get_status",
        new_callable=AsyncMock,
        return_value=None,
    ):
        r = await client.get(f"/api/v1/my/articles/{aid}/status")
    assert r.status_code == 200
    body = r.json()
    assert body["article_id"] == aid
    assert body["user_id"] == authed_user_id
    assert body["is_read"] is False
    assert body["is_starred"] is False
    assert body["is_later"] is False


@pytest.mark.asyncio
async def test_put_status_updates_fields(client, authed_user_id):
    aid = str(uuid.uuid4())
    out = _sample_status(
        user_id=authed_user_id, article_id=aid, is_read=True, is_starred=True
    )
    with patch(
        "app.routers.reading.reading_service.upsert_status",
        new_callable=AsyncMock,
        return_value=out,
    ) as mock_up:
        r = await client.put(
            f"/api/v1/my/articles/{aid}/status",
            json={"is_read": True, "is_starred": True},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["is_read"] is True
    assert body["is_starred"] is True
    mock_up.assert_awaited_once()
    assert mock_up.await_args.kwargs["is_read"] is True
    assert mock_up.await_args.kwargs["is_starred"] is True


@pytest.mark.asyncio
async def test_put_status_requires_field(client, authed_user_id):
    aid = str(uuid.uuid4())
    r = await client.put(f"/api/v1/my/articles/{aid}/status", json={})
    assert r.status_code == 400
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_original_click(client, authed_user_id):
    aid = str(uuid.uuid4())
    out = _sample_status(
        user_id=authed_user_id,
        article_id=aid,
        is_read=True,
        original_clicked_at=datetime.now(timezone.utc),
    )
    with patch(
        "app.routers.reading.reading_service.mark_original_click",
        new_callable=AsyncMock,
        return_value=out,
    ) as mock_click:
        r = await client.post(f"/api/v1/my/articles/{aid}/original-click")
    assert r.status_code == 200
    assert r.json() == {"message": "recorded"}
    mock_click.assert_awaited_once()


@pytest.mark.asyncio
async def test_reading_without_auth_401(client):
    aid = str(uuid.uuid4())
    r = await client.get(f"/api/v1/my/articles/{aid}/status")
    assert r.status_code == 401
