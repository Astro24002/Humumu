"""Public catalog visibility: public_only filter on journal list API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import app
from app.schemas.journal import JournalOut


class _EmptySession:
    async def execute(self, statement):  # noqa: ANN001
        raise AssertionError("unused")


def _j(**kw):
    base = dict(
        id=str(uuid.uuid4()),
        name="X",
        slug="x",
        source_type="rss",
        source_url="https://ex.com/x.rss",
        description="",
        fetch_interval=1800,
        is_active=True,
        created_by=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        directory_status="public",
        content_type="journal",
    )
    base.update(kw)
    return JournalOut.model_validate(base)


@pytest.fixture
async def client():
    async def ov():
        yield _EmptySession()

    app.dependency_overrides[get_session] = ov
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_public_list_calls_list_journals_public_only(client):
    with patch(
        "app.routers.journals.journal_service.list_journals",
        new_callable=AsyncMock,
        return_value=[_j(directory_status="public")],
    ) as m:
        r = await client.get("/api/v1/journals")
    assert r.status_code == 200
    assert all(j["directory_status"] == "public" for j in r.json()["journals"])
    # default public_only should be True when kwargs used; also accept positional-only
    if m.await_args is not None:
        kwargs = m.await_args.kwargs or {}
        if "public_only" in kwargs:
            assert kwargs["public_only"] is True


@pytest.mark.asyncio
async def test_admin_list_passes_public_only_false(client):
    from app.deps import require_admin

    uid = str(uuid.uuid4())

    async def override_admin():
        return uid

    app.dependency_overrides[require_admin] = override_admin
    with patch(
        "app.routers.admin.journal_service.list_journals",
        new_callable=AsyncMock,
        return_value=[_j(directory_status="private")],
    ) as m:
        r = await client.get("/api/v1/admin/journals")
    assert r.status_code == 200
    assert m.await_args is not None
    assert m.await_args.kwargs.get("public_only") is False
    app.dependency_overrides.pop(require_admin, None)
