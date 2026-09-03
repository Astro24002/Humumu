"""ASGI tests for journals/articles public APIs and my feed (no live Postgres)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import app
from app.schemas.article import ArticleOut
from app.schemas.journal import JournalOut


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


def _sample_article(**overrides) -> ArticleOut:
    data = {
        "id": str(uuid.uuid4()),
        "doi": "10.1000/test",
        "title": "Sample Article",
        "authors": ["Ada Lovelace"],
        "abstract": "An abstract",
        "journal_id": str(uuid.uuid4()),
        "journal_name": "Nature",
        "journal_source_type": "rss",
        "content_type": "journal",
        "publish_date": date(2026, 5, 1),
        "url": "https://example.com/a",
        "fetched_at": datetime(2026, 5, 2, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return ArticleOut.model_validate(data)


class _EmptySession:
    """Session stand-in; services are patched so execute is unused."""

    async def execute(self, statement):  # noqa: ANN001
        raise AssertionError("session.execute should not be called when services are mocked")


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
async def test_list_journals_has_journals_key(client):
    j = _sample_journal()
    with patch(
        "app.routers.journals.journal_service.list_journals",
        new_callable=AsyncMock,
        return_value=([j], 1),
    ):
        r = await client.get("/api/v1/journals")
    assert r.status_code == 200
    body = r.json()
    assert "journals" in body
    assert isinstance(body["journals"], list)
    assert len(body["journals"]) == 1
    assert body["journals"][0]["name"] == "Nature"
    assert body["journals"][0]["article_count"] == 3
    assert body["journals"][0]["fetch_interval"] == 1800
    assert isinstance(body["journals"][0]["fetch_interval"], int)


@pytest.mark.asyncio
async def test_list_journals_empty(client):
    with patch(
        "app.routers.journals.journal_service.list_journals",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        r = await client.get("/api/v1/journals")
    assert r.status_code == 200
    body = r.json()
    assert body["journals"] == []
    assert body.get("total", 0) == 0


@pytest.mark.asyncio
async def test_list_journals_pagination_params(client):
    j = _sample_journal()
    with patch(
        "app.routers.journals.journal_service.list_journals",
        new_callable=AsyncMock,
        return_value=([j], 12),
    ) as mock_list:
        r = await client.get("/api/v1/journals?limit=5&offset=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 12
    assert len(body["journals"]) == 1
    kwargs = mock_list.await_args.kwargs
    assert kwargs.get("limit") == 5
    assert kwargs.get("offset") == 10



@pytest.mark.asyncio
async def test_get_journal_bare(client):
    j = _sample_journal(name="Science")
    with patch(
        "app.routers.journals.journal_service.get_journal",
        new_callable=AsyncMock,
        return_value=j,
    ) as mock_get:
        r = await client.get(f"/api/v1/journals/{j.id}")
    mock_get.assert_awaited_once()
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == j.id
    assert body["name"] == "Science"
    assert "journals" not in body


@pytest.mark.asyncio
async def test_get_missing_journal_404(client):
    missing = str(uuid.uuid4())
    with patch(
        "app.routers.journals.journal_service.get_journal",
        new_callable=AsyncMock,
        return_value=None,
    ):
        r = await client.get(f"/api/v1/journals/{missing}")
    assert r.status_code == 404
    assert r.json() == {"error": "journal not found"}


@pytest.mark.asyncio
async def test_list_articles_shape(client):
    a = _sample_article()
    with (
        patch(
            "app.routers.articles.article_service.list_articles",
            new_callable=AsyncMock,
            return_value=[a],
        ) as mock_list,
        patch(
            "app.routers.articles.article_service.count_list_articles",
            new_callable=AsyncMock,
            return_value=42,
        ) as mock_count,
    ):
        r = await client.get("/api/v1/articles?limit=10&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert "articles" in body
    assert body["total"] == 42
    assert len(body["articles"]) == 1
    assert body["articles"][0]["title"] == "Sample Article"
    assert body["articles"][0]["journal_name"] == "Nature"
    assert body["articles"][0]["journal_source_type"] == "rss"
    assert body["articles"][0]["content_type"] == "journal"
    kwargs = mock_list.await_args.kwargs
    assert kwargs["limit"] == 10
    assert kwargs["offset"] == 0
    mock_count.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_articles_with_journal_id(client):
    jid = str(uuid.uuid4())
    with (
        patch(
            "app.routers.articles.article_service.list_articles",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_list,
        patch(
            "app.routers.articles.article_service.count_list_articles",
            new_callable=AsyncMock,
            return_value=0,
        ),
    ):
        r = await client.get(f"/api/v1/articles?journal_id={jid}")
    assert r.status_code == 200
    assert r.json() == {"articles": [], "total": 0}
    assert mock_list.await_args.kwargs["journal_id"] == jid


@pytest.mark.asyncio
async def test_list_articles_with_content_type(client):
    with (
        patch(
            "app.routers.articles.article_service.list_articles",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_list,
        patch(
            "app.routers.articles.article_service.count_list_articles",
            new_callable=AsyncMock,
            return_value=0,
        ) as mock_count,
    ):
        r = await client.get("/api/v1/articles?content_type=preprint")
    assert r.status_code == 200
    assert mock_list.await_args.kwargs["content_type"] == "preprint"
    assert mock_count.await_args.kwargs["content_type"] == "preprint"


@pytest.mark.asyncio
async def test_get_article_bare(client):
    a = _sample_article(title="Bare Article")
    with patch(
        "app.routers.articles.article_service.get_article",
        new_callable=AsyncMock,
        return_value=a,
    ):
        r = await client.get(f"/api/v1/articles/{a.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Bare Article"
    assert "articles" not in body


@pytest.mark.asyncio
async def test_get_missing_article_404(client):
    missing = str(uuid.uuid4())
    with patch(
        "app.routers.articles.article_service.get_article",
        new_callable=AsyncMock,
        return_value=None,
    ):
        r = await client.get(f"/api/v1/articles/{missing}")
    assert r.status_code == 404
    assert r.json() == {"error": "article not found"}


@pytest.mark.asyncio
async def test_my_feed_without_auth_401(client):
    r = await client.get("/api/v1/my/feed")
    assert r.status_code == 401
    body = r.json()
    assert "error" in body


@pytest.mark.asyncio
async def test_my_feed_with_auth(client):
    user_id = str(uuid.uuid4())
    a = _sample_article(title="Feed Item")

    async def override_user_id():
        return user_id

    from app.deps import get_current_user_id

    app.dependency_overrides[get_current_user_id] = override_user_id
    try:
        with patch(
            "app.routers.articles.article_service.list_feed_for_user",
            new_callable=AsyncMock,
            return_value=[a],
        ) as mock_feed:
            r = await client.get("/api/v1/my/feed?limit=5&offset=1")
        assert r.status_code == 200
        body = r.json()
        assert body["articles"][0]["title"] == "Feed Item"
        assert mock_feed.await_args.args[1] == user_id
        assert mock_feed.await_args.kwargs["limit"] == 5
        assert mock_feed.await_args.kwargs["offset"] == 1
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_fetch_interval_timedelta_serializes_as_int_seconds():
    """JournalOut converts timedelta fetch_interval to integer seconds."""
    j = JournalOut.model_validate(
        {
            "id": str(uuid.uuid4()),
            "name": "Interval Test",
            "slug": "interval-test",
            "source_type": "rss",
            "source_url": "https://example.com/x.rss",
            "description": "",
            "fetch_interval": timedelta(minutes=30),
            "is_active": True,
            "created_by": None,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "article_count": 0,
            "last_article_date": None,
        }
    )
    assert j.fetch_interval == 1800
    dumped = j.model_dump()
    assert dumped["fetch_interval"] == 1800
    assert isinstance(dumped["fetch_interval"], int)
