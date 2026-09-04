"""ASGI tests for journal requests and user RSS self-service (no live network/DB)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.db import get_session
from app.deps import get_current_user_id
from app.main import app
from app.schemas.journal import JournalOut, JournalRequestOut
from app.services.fetcher_meta import fetch_feed_meta

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Nature News</title>
    <link>https://example.com/nature</link>
    <description>Science news feed</description>
    <item>
      <title>First Article</title>
      <link>https://example.com/a1</link>
      <description>Hello</description>
    </item>
  </channel>
</rss>
"""


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
        "description": "",
        "fetch_interval": 1800,
        "is_active": True,
        "created_by": None,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "article_count": 0,
        "last_article_date": None,
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

    app.dependency_overrides[get_current_user_id] = override_user_id
    yield user_id
    app.dependency_overrides.pop(get_current_user_id, None)


# --- fetcher_meta unit (mocked httpx) ---


@pytest.mark.asyncio
async def test_fetch_feed_meta_parses_rss_title():
    mock_resp = MagicMock(spec=Response)
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_RSS_XML

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.services.fetcher_meta.safe_get_text",
        new_callable=AsyncMock,
        return_value=("https://example.com/feed.rss", SAMPLE_RSS_XML, {}),
    ) as mock_get:
        meta = await fetch_feed_meta("https://example.com/feed.rss")

    assert meta["name"] == "Nature News"
    assert meta["title"] == "Nature News"
    assert meta["source_type"] == "rss"
    assert "items" in meta
    mock_get.assert_awaited_once()
    assert mock_get.await_args.args[0] == "https://example.com/feed.rss"


# --- preview ---


@pytest.mark.asyncio
async def test_preview_success(client, authed_user_id):
    with patch(
        "app.routers.user_journals.fetch_feed_meta",
        new_callable=AsyncMock,
        return_value={"name": "Nature News", "title": "Nature News", "source_type": "rss"},
    ) as mock_fetch:
        r = await client.post(
            "/api/v1/my/journals/preview",
            json={"source_url": "https://example.com/feed.rss"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Nature News"
    assert body["source_type"] == "rss"
    assert body.get("items") == []
    mock_fetch.assert_awaited_once_with("https://example.com/feed.rss")


@pytest.mark.asyncio
async def test_preview_fetch_failure_message(client, authed_user_id):
    with patch(
        "app.routers.user_journals.fetch_feed_meta",
        new_callable=AsyncMock,
        side_effect=RuntimeError("network down"),
    ):
        r = await client.post(
            "/api/v1/my/journals/preview",
            json={"source_url": "https://example.com/bad.rss"},
        )
    assert r.status_code == 400
    assert r.json() == {"error": "cannot fetch feed from this URL"}


@pytest.mark.asyncio
async def test_preview_invalid_body(client, authed_user_id):
    r = await client.post("/api/v1/my/journals/preview", json={"source_url": "not-a-url"})
    assert r.status_code == 400
    assert r.json() == {"error": "valid source_url is required"}


# --- journal requests ---


@pytest.mark.asyncio
async def test_create_request_201_bare_shape(client, authed_user_id):
    jr = _sample_request(user_id=authed_user_id)
    with patch(
        "app.routers.requests.journal_service.create_journal_request",
        new_callable=AsyncMock,
        return_value=jr,
    ) as mock_create:
        r = await client.post(
            "/api/v1/journals/requests",
            json={
                "journal_name": "Wanted Journal",
                "source_url": "https://example.com/wanted.rss",
            },
        )
    assert r.status_code == 201
    body = r.json()
    # bare JournalRequestOut — not wrapped in {"request": ...}
    assert "requests" not in body
    assert body["id"] == jr.id
    assert body["journal_name"] == "Wanted Journal"
    assert body["status"] == "pending"
    assert body["user_id"] == authed_user_id
    mock_create.assert_awaited_once()
    assert mock_create.await_args.kwargs["user_id"] == authed_user_id


@pytest.mark.asyncio
async def test_list_requests_wrapped(client, authed_user_id):
    jr = _sample_request(user_id=authed_user_id)
    with patch(
        "app.routers.requests.journal_service.list_journal_requests_by_user",
        new_callable=AsyncMock,
        return_value=[jr],
    ):
        r = await client.get("/api/v1/journals/requests")
    assert r.status_code == 200
    body = r.json()
    assert "requests" in body
    assert len(body["requests"]) == 1
    assert body["requests"][0]["id"] == jr.id


@pytest.mark.asyncio
async def test_journals_requests_not_swallowed_by_journal_id(client, authed_user_id):
    """Ensure GET /journals/requests is not treated as /journals/{journal_id}."""
    with patch(
        "app.routers.requests.journal_service.list_journal_requests_by_user",
        new_callable=AsyncMock,
        return_value=[],
    ):
        r = await client.get("/api/v1/journals/requests")
    assert r.status_code == 200
    assert r.json() == {"requests": [], "total": 0}


# --- create my journal ---


@pytest.mark.asyncio
async def test_create_my_journal_already_existed(client, authed_user_id):
    existing = _sample_journal(source_url="https://example.com/nature.rss")
    with (
        patch(
            "app.routers.user_journals.journal_service.find_by_url",
            new_callable=AsyncMock,
            return_value=existing,
        ),
        patch(
            "app.routers.user_journals.sub_service.subscribe_journal",
            new_callable=AsyncMock,
        ) as mock_sub,
        patch(
            "app.routers.user_journals.journal_service.create_journal",
            new_callable=AsyncMock,
        ) as mock_create,
    ):
        r = await client.post(
            "/api/v1/my/journals",
            json={"name": "Nature", "source_url": "https://example.com/nature.rss"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["already_existed"] is True
    assert body["journal"]["id"] == existing.id
    mock_sub.assert_awaited_once()
    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_my_journal_new_201(client, authed_user_id):
    created = _sample_journal(
        name="New Journal",
        slug="new-journal",
        source_url="https://example.com/new.rss",
        created_by=authed_user_id,
    )
    with (
        patch(
            "app.routers.user_journals.journal_service.find_by_url",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.routers.user_journals.journal_service.create_journal",
            new_callable=AsyncMock,
            return_value=created,
        ) as mock_create,
        patch(
            "app.routers.user_journals.sub_service.subscribe_journal",
            new_callable=AsyncMock,
        ) as mock_sub,
    ):
        r = await client.post(
            "/api/v1/my/journals",
            json={"name": "New Journal", "source_url": "https://example.com/new.rss"},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["already_existed"] is False
    assert body["journal"]["name"] == "New Journal"
    mock_create.assert_awaited_once()
    mock_sub.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_my_journal_bad_body(client, authed_user_id):
    r = await client.post("/api/v1/my/journals", json={"name": "", "source_url": ""})
    assert r.status_code == 400
    assert r.json() == {"error": "name and source_url are required"}


def test_slugify_matches_go_intent():
    from app.services.journals import slugify

    assert slugify("Nature News") == "nature-news"
    assert slugify("Hello!!! World") == "hello-world"
    assert slugify("中文期刊") == "中文期刊"
    assert slugify("@@@") == "journal"
    assert slugify("  Foo   Bar  ") == "foo-bar"
