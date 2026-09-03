"""Admin RBAC: any JWT is not enough; is_admin required."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.deps import get_current_user_id, require_admin
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


@pytest.mark.asyncio
async def test_admin_stats_401_without_token(client):
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_current_user_id, None)
    r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_stats_403_for_non_admin(client):
    async def override_require_admin():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="admin required")

    app.dependency_overrides[require_admin] = override_require_admin
    r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 403
    assert r.json()["error"] == "admin required"
    app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_admin_stats_200_for_admin(client):
    uid = str(uuid.uuid4())

    async def override_require_admin():
        return uid

    app.dependency_overrides[require_admin] = override_require_admin
    with (
        patch(
            "app.routers.admin.journal_service.count_journals",
            new_callable=AsyncMock,
            return_value=1,
        ),
        patch(
            "app.routers.admin.article_service.count_articles",
            new_callable=AsyncMock,
            return_value=2,
        ),
        patch(
            "app.routers.admin.user_service.count_users",
            new_callable=AsyncMock,
            return_value=3,
        ),
        patch(
            "app.routers.admin.journal_service.count_pending_requests",
            new_callable=AsyncMock,
            return_value=0,
        ),
    ):
        r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 200
    assert r.json()["journal_count"] == 1
    app.dependency_overrides.pop(require_admin, None)
