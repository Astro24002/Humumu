"""ASGI tests for subscriptions, settings, and notifications (no live Postgres)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.deps import get_current_user_id
from app.main import app
from app.schemas.journal import JournalOut
from app.schemas.notification import NotificationOut
from app.schemas.subscription import AuthorTrackingOut, KeywordSubscriptionOut


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


def _sample_notification(**overrides) -> NotificationOut:
    data = {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "article_id": str(uuid.uuid4()),
        "channel": "email",
        "status": "sent",
        "error_message": None,
        "match_reasons": "journal,keyword",
        "created_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "sent_at": datetime(2026, 6, 1, 1, tzinfo=timezone.utc),
        "article_title": "Sample paper title",
    }
    data.update(overrides)
    return NotificationOut.model_validate(data)


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


@pytest.mark.asyncio
async def test_subscribe_journal_message_shape(client, authed_user_id):
    jid = str(uuid.uuid4())
    with (
        patch(
            "app.routers.subscriptions.sub_service.can_subscribe",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.routers.subscriptions.sub_service.subscribe_journal",
            new_callable=AsyncMock,
        ) as mock_sub,
    ):
        r = await client.post(f"/api/v1/subscriptions/journals/{jid}")
    assert r.status_code == 200
    assert r.json() == {"message": "subscribed"}
    mock_sub.assert_awaited_once()
    assert mock_sub.await_args.args[1] == authed_user_id
    assert mock_sub.await_args.args[2] == jid


@pytest.mark.asyncio
async def test_subscribe_missing_journal_404(client, authed_user_id):
    jid = str(uuid.uuid4())
    with patch(
        "app.routers.subscriptions.sub_service.can_subscribe",
        new_callable=AsyncMock,
        return_value=False,
    ):
        r = await client.post(f"/api/v1/subscriptions/journals/{jid}")
    assert r.status_code == 404
    assert r.json() == {"error": "journal not found"}


@pytest.mark.asyncio
async def test_unsubscribe_journal_message(client, authed_user_id):
    jid = str(uuid.uuid4())
    with patch(
        "app.routers.subscriptions.sub_service.unsubscribe_journal",
        new_callable=AsyncMock,
    ):
        r = await client.delete(f"/api/v1/subscriptions/journals/{jid}")
    assert r.status_code == 200
    assert r.json() == {"message": "unsubscribed"}


@pytest.mark.asyncio
async def test_list_subscribed_journals_shape(client, authed_user_id):
    j = _sample_journal()
    with patch(
        "app.routers.subscriptions.sub_service.list_subscribed_journals",
        new_callable=AsyncMock,
        return_value=[j],
    ):
        r = await client.get("/api/v1/subscriptions/journals")
    assert r.status_code == 200
    body = r.json()
    assert "journals" in body
    assert body["journals"][0]["name"] == "Nature"


@pytest.mark.asyncio
async def test_subscriptions_without_auth_401(client):
    r = await client.get("/api/v1/subscriptions/journals")
    assert r.status_code == 401
    assert "error" in r.json()

    r = await client.post(f"/api/v1/subscriptions/journals/{uuid.uuid4()}")
    assert r.status_code == 401

    r = await client.put("/api/v1/settings/push-frequency", json={"push_frequency": "daily"})
    assert r.status_code == 401

    r = await client.get("/api/v1/notifications")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_add_author_201(client, authed_user_id):
    with patch(
        "app.routers.subscriptions.sub_service.add_author",
        new_callable=AsyncMock,
    ) as mock_add:
        r = await client.post(
            "/api/v1/subscriptions/authors",
            json={"author_name": "Ada Lovelace"},
        )
    assert r.status_code == 201
    assert r.json() == {"message": "author added"}
    mock_add.assert_awaited_once()
    assert mock_add.await_args.args[2] == "Ada Lovelace"


@pytest.mark.asyncio
async def test_list_authors_shape(client, authed_user_id):
    author = AuthorTrackingOut.model_validate(
        {
            "id": str(uuid.uuid4()),
            "user_id": authed_user_id,
            "author_name": "Ada",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    )
    with patch(
        "app.routers.subscriptions.sub_service.list_authors",
        new_callable=AsyncMock,
        return_value=[author],
    ):
        r = await client.get("/api/v1/subscriptions/authors")
    assert r.status_code == 200
    body = r.json()
    assert body["authors"][0]["author_name"] == "Ada"


@pytest.mark.asyncio
async def test_remove_author_message(client, authed_user_id):
    aid = str(uuid.uuid4())
    with patch(
        "app.routers.subscriptions.sub_service.remove_author",
        new_callable=AsyncMock,
    ):
        r = await client.delete(f"/api/v1/subscriptions/authors/{aid}")
    assert r.status_code == 200
    assert r.json() == {"message": "author removed"}


@pytest.mark.asyncio
async def test_add_keyword_201(client, authed_user_id):
    with patch(
        "app.routers.subscriptions.sub_service.add_keyword",
        new_callable=AsyncMock,
    ):
        r = await client.post(
            "/api/v1/subscriptions/keywords",
            json={"keyword": "CRISPR"},
        )
    assert r.status_code == 201
    assert r.json() == {"message": "keyword added"}


@pytest.mark.asyncio
async def test_list_keywords_shape(client, authed_user_id):
    kw = KeywordSubscriptionOut.model_validate(
        {
            "id": str(uuid.uuid4()),
            "user_id": authed_user_id,
            "keyword": "CRISPR",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    )
    with patch(
        "app.routers.subscriptions.sub_service.list_keywords",
        new_callable=AsyncMock,
        return_value=[kw],
    ):
        r = await client.get("/api/v1/subscriptions/keywords")
    assert r.status_code == 200
    assert r.json()["keywords"][0]["keyword"] == "CRISPR"


@pytest.mark.asyncio
async def test_remove_keyword_message(client, authed_user_id):
    kid = str(uuid.uuid4())
    with patch(
        "app.routers.subscriptions.sub_service.remove_keyword",
        new_callable=AsyncMock,
    ):
        r = await client.delete(f"/api/v1/subscriptions/keywords/{kid}")
    assert r.status_code == 200
    assert r.json() == {"message": "keyword removed"}


@pytest.mark.asyncio
async def test_push_frequency_validation_400(client, authed_user_id):
    r = await client.put(
        "/api/v1/settings/push-frequency",
        json={"push_frequency": "weekly"},
    )
    assert r.status_code == 400
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_push_frequency_success(client, authed_user_id):
    with patch(
        "app.routers.settings.user_service.update_push_frequency",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_upd:
        r = await client.put(
            "/api/v1/settings/push-frequency",
            json={"push_frequency": "daily"},
        )
    assert r.status_code == 200
    assert r.json() == {"message": "settings updated"}
    mock_upd.assert_awaited_once()
    assert mock_upd.await_args.args[1] == authed_user_id
    assert mock_upd.await_args.args[2] == "daily"


@pytest.mark.asyncio
async def test_notifications_list_shape(client, authed_user_id):
    n = _sample_notification(user_id=authed_user_id)
    with patch(
        "app.routers.notifications.sub_service.list_notifications",
        new_callable=AsyncMock,
        return_value=([n], 7),
    ) as mock_list:
        r = await client.get("/api/v1/notifications?limit=10&offset=2")
    assert r.status_code == 200
    body = r.json()
    assert "notifications" in body
    assert body["total"] == 7
    assert len(body["notifications"]) == 1
    assert body["notifications"][0]["channel"] == "email"
    assert body["notifications"][0]["status"] == "sent"
    assert body["notifications"][0]["match_reasons"] == ["journal", "keyword"]
    assert body["notifications"][0]["article_title"] == "Sample paper title"
    assert mock_list.await_args.args[1] == authed_user_id
    assert mock_list.await_args.kwargs["limit"] == 10
    assert mock_list.await_args.kwargs["offset"] == 2


@pytest.mark.asyncio
async def test_notifications_status_filter_forwarded(client, authed_user_id):
    with patch(
        "app.routers.notifications.sub_service.list_notifications",
        new_callable=AsyncMock,
        return_value=([], 0),
    ) as mock_list:
        r = await client.get("/api/v1/notifications?status=failed&limit=5")
    assert r.status_code == 200
    assert r.json() == {"notifications": [], "total": 0}
    assert mock_list.await_args.kwargs["status"] == "failed"
    assert mock_list.await_args.kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_notifications_channel_filter_forwarded(client, authed_user_id):
    with patch(
        "app.routers.notifications.sub_service.list_notifications",
        new_callable=AsyncMock,
        return_value=([], 0),
    ) as mock_list:
        r = await client.get("/api/v1/notifications?channel=wechat&status=sent")
    assert r.status_code == 200
    assert mock_list.await_args.kwargs["channel"] == "wechat"
    assert mock_list.await_args.kwargs["status"] == "sent"


@pytest.mark.asyncio
async def test_notifications_empty(client, authed_user_id):
    with patch(
        "app.routers.notifications.sub_service.list_notifications",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        r = await client.get("/api/v1/notifications")
    assert r.status_code == 200
    assert r.json() == {"notifications": [], "total": 0}
