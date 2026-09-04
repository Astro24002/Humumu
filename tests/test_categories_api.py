"""ASGI tests for CAS category public/admin APIs."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.deps import get_current_user_id, require_admin
from app.main import app
from app.schemas.category import CasCategoryOut


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
def admin_user_id():
    uid = str(uuid.uuid4())

    async def override_admin():
        return uid

    app.dependency_overrides[require_admin] = override_admin
    app.dependency_overrides[get_current_user_id] = override_admin
    return uid


def _cat(**overrides) -> CasCategoryOut:
    data = {
        "id": str(uuid.uuid4()),
        "year": 2025,
        "major": "数学",
        "minor": "计算数学",
        "zone": 1,
        "is_top": True,
    }
    data.update(overrides)
    return CasCategoryOut(**data)


@pytest.mark.asyncio
async def test_public_list_cas_categories(client):
    cat = _cat()
    list_mock = AsyncMock(return_value=[cat])
    with (
        patch(
            "app.routers.categories.cat_service.list_categories",
            new=list_mock,
        ),
        patch(
            "app.routers.categories.cat_service.list_years",
            new_callable=AsyncMock,
            return_value=[2025, 2023],
        ),
    ):
        r = await client.get("/api/v1/categories/cas?year=2025&major=%E6%95%B0%E5%AD%A6")
    assert r.status_code == 200
    body = r.json()
    assert body["years"] == [2025, 2023]
    assert body["categories"][0]["major"] == "数学"
    assert body["categories"][0]["zone"] == 1
    list_mock.assert_awaited_once()
    kwargs = list_mock.await_args.kwargs
    assert kwargs.get("year") == 2025
    assert kwargs.get("major") == "数学"


@pytest.mark.asyncio
async def test_admin_create_cas_category(client, admin_user_id):
    cat = _cat()
    with patch(
        "app.routers.admin.cat_service.create_category",
        new_callable=AsyncMock,
        return_value=cat,
    ) as mock_create:
        r = await client.post(
            "/api/v1/admin/cas/categories",
            json={
                "year": 2025,
                "major": "数学",
                "minor": "计算数学",
                "zone": 1,
                "is_top": True,
            },
        )
    assert r.status_code == 201
    assert r.json()["minor"] == "计算数学"
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_attach_cas(client, admin_user_id):
    jid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    with patch(
        "app.routers.admin.cat_service.attach_categories",
        new_callable=AsyncMock,
        return_value=1,
    ) as mock_att:
        r = await client.post(
            f"/api/v1/admin/journals/{jid}/cas",
            json={"category_ids": [cid]},
        )
    assert r.status_code == 200
    assert r.json() == {"message": "categories attached"}
    mock_att.assert_awaited_once()
