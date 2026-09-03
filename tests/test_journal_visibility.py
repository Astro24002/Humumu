"""Public catalog visibility: public_only filter + owner access on get."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import app
from app.schemas.article import ArticleOut
from app.schemas.journal import JournalOut
from app.services import articles as article_service
from app.services import journals as journal_service


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


def _a(**kw):
    base = dict(
        id=str(uuid.uuid4()),
        doi="10.1/x",
        title="T",
        authors=["A"],
        abstract="",
        journal_id=str(uuid.uuid4()),
        journal_name="X",
        journal_source_type="rss",
        content_type="journal",
        publish_date=date(2026, 1, 1),
        url="https://ex.com/a",
        fetched_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    base.update(kw)
    return ArticleOut.model_validate(base)


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


@pytest.mark.asyncio
async def test_get_journal_passes_viewer_user_id(client):
    from app.deps import get_optional_user_id

    uid = str(uuid.uuid4())
    j = _j(directory_status="private", created_by=uid)

    async def override_opt():
        return uid

    app.dependency_overrides[get_optional_user_id] = override_opt
    try:
        with patch(
            "app.routers.journals.journal_service.get_journal",
            new_callable=AsyncMock,
            return_value=j,
        ) as m:
            r = await client.get(f"/api/v1/journals/{j.id}")
        assert r.status_code == 200
        assert m.await_args.kwargs.get("viewer_user_id") == uid
    finally:
        app.dependency_overrides.pop(get_optional_user_id, None)


@pytest.mark.asyncio
async def test_get_article_passes_viewer_user_id(client):
    from app.deps import get_optional_user_id

    uid = str(uuid.uuid4())
    a = _a()

    async def override_opt():
        return uid

    app.dependency_overrides[get_optional_user_id] = override_opt
    try:
        with patch(
            "app.routers.articles.article_service.get_article",
            new_callable=AsyncMock,
            return_value=a,
        ) as m:
            r = await client.get(f"/api/v1/articles/{a.id}")
        assert r.status_code == 200
        assert m.await_args.kwargs.get("viewer_user_id") == uid
    finally:
        app.dependency_overrides.pop(get_optional_user_id, None)


@pytest.mark.asyncio
async def test_get_article_anonymous_passes_none_viewer(client):
    a = _a()
    with patch(
        "app.routers.articles.article_service.get_article",
        new_callable=AsyncMock,
        return_value=a,
    ) as m:
        r = await client.get(f"/api/v1/articles/{a.id}")
    assert r.status_code == 200
    assert m.await_args.kwargs.get("viewer_user_id") is None


@pytest.mark.asyncio
async def test_list_articles_passes_viewer_with_journal_id(client):
    from app.deps import get_optional_user_id

    uid = str(uuid.uuid4())
    jid = str(uuid.uuid4())

    async def override_opt():
        return uid

    app.dependency_overrides[get_optional_user_id] = override_opt
    try:
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
            r = await client.get(f"/api/v1/articles?journal_id={jid}")
        assert r.status_code == 200
        assert mock_list.await_args.kwargs.get("viewer_user_id") == uid
        assert mock_list.await_args.kwargs.get("journal_id") == jid
        assert mock_count.await_args.kwargs.get("viewer_user_id") == uid
    finally:
        app.dependency_overrides.pop(get_optional_user_id, None)


def _result_one(row):
    result = MagicMock()
    result.one_or_none.return_value = row
    return result


@pytest.mark.asyncio
async def test_service_get_article_public_ok_anonymous():
    aid = uuid.uuid4()
    jid = uuid.uuid4()
    article = SimpleNamespace(
        id=aid,
        doi="",
        title="Pub",
        authors=[],
        abstract="",
        journal_id=jid,
        publish_date=None,
        url="",
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=_result_one(
            (article, "J", "rss", "journal", "public", uuid.uuid4(), jid)
        )
    )
    out = await article_service.get_article(session, aid, viewer_user_id=None)
    assert out is not None
    assert out.title == "Pub"


@pytest.mark.asyncio
async def test_service_get_article_private_owner_ok():
    owner = uuid.uuid4()
    aid = uuid.uuid4()
    jid = uuid.uuid4()
    article = SimpleNamespace(
        id=aid,
        doi="",
        title="Priv",
        authors=[],
        abstract="",
        journal_id=jid,
        publish_date=None,
        url="",
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=_result_one(
            (article, "J", "rss", "journal", "private", owner, jid)
        )
    )
    out = await article_service.get_article(session, aid, viewer_user_id=str(owner))
    assert out is not None
    assert out.title == "Priv"


@pytest.mark.asyncio
async def test_service_get_article_private_stranger_none():
    owner = uuid.uuid4()
    stranger = uuid.uuid4()
    aid = uuid.uuid4()
    jid = uuid.uuid4()
    article = SimpleNamespace(
        id=aid,
        doi="",
        title="Priv",
        authors=[],
        abstract="",
        journal_id=jid,
        publish_date=None,
        url="",
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session = AsyncMock()
    # get_article now returns journal_pk as 7th column
    session.execute = AsyncMock(
        return_value=_result_one(
            (article, "J", "rss", "journal", "private", owner, jid)
        )
    )
    with patch(
        "app.services.subscriptions.is_subscribed",
        new_callable=AsyncMock,
        return_value=False,
    ):
        out = await article_service.get_article(session, aid, viewer_user_id=str(stranger))
        assert out is None
        out_anon = await article_service.get_article(session, aid, viewer_user_id=None)
        assert out_anon is None


@pytest.mark.asyncio
async def test_service_get_article_private_subscriber_ok():
    owner = uuid.uuid4()
    subscriber = uuid.uuid4()
    aid = uuid.uuid4()
    jid = uuid.uuid4()
    article = SimpleNamespace(
        id=aid,
        doi="",
        title="SubPriv",
        authors=[],
        abstract="",
        journal_id=jid,
        publish_date=None,
        url="",
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=_result_one(
            (article, "J", "rss", "journal", "private", owner, jid)
        )
    )
    with patch(
        "app.services.subscriptions.is_subscribed",
        new_callable=AsyncMock,
        return_value=True,
    ):
        out = await article_service.get_article(
            session, aid, viewer_user_id=str(subscriber)
        )
    assert out is not None
    assert out.title == "SubPriv"


@pytest.mark.asyncio
async def test_service_get_journal_private_owner_ok():
    owner = uuid.uuid4()
    jid = uuid.uuid4()
    journal = SimpleNamespace(
        id=jid,
        name="Mine",
        slug="mine",
        source_type="rss",
        source_url="https://ex.com/m.rss",
        description="",
        fetch_interval=None,
        is_active=True,
        created_by=owner,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        content_type="journal",
        directory_status="private",
        homepage_url="",
        consecutive_failures=0,
        last_error=None,
        last_success_at=None,
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result_one((journal, 0, None)))
    out = await journal_service.get_journal(session, jid, viewer_user_id=owner)
    assert out is not None
    assert out.name == "Mine"
    assert out.directory_status == "private"


@pytest.mark.asyncio
async def test_service_get_journal_private_stranger_none():
    owner = uuid.uuid4()
    stranger = uuid.uuid4()
    jid = uuid.uuid4()
    journal = SimpleNamespace(
        id=jid,
        name="Mine",
        slug="mine",
        source_type="rss",
        source_url="https://ex.com/m.rss",
        description="",
        fetch_interval=None,
        is_active=True,
        created_by=owner,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        content_type="journal",
        directory_status="private",
        homepage_url="",
        consecutive_failures=0,
        last_error=None,
        last_success_at=None,
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result_one((journal, 0, None)))
    with patch(
        "app.services.subscriptions.is_subscribed",
        new_callable=AsyncMock,
        return_value=False,
    ):
        assert await journal_service.get_journal(session, jid, viewer_user_id=stranger) is None
        assert await journal_service.get_journal(session, jid, viewer_user_id=None) is None


@pytest.mark.asyncio
async def test_service_get_journal_private_subscriber_ok():
    owner = uuid.uuid4()
    subscriber = uuid.uuid4()
    jid = uuid.uuid4()
    journal = SimpleNamespace(
        id=jid,
        name="SharedPriv",
        slug="shared-priv",
        source_type="rss",
        source_url="https://ex.com/s.rss",
        description="",
        fetch_interval=None,
        is_active=True,
        created_by=owner,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        content_type="journal",
        directory_status="private",
        homepage_url="",
        consecutive_failures=0,
        last_error=None,
        last_success_at=None,
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result_one((journal, 0, None)))
    with patch(
        "app.services.subscriptions.is_subscribed",
        new_callable=AsyncMock,
        return_value=True,
    ):
        out = await journal_service.get_journal(session, jid, viewer_user_id=subscriber)
    assert out is not None
    assert out.name == "SharedPriv"


def test_article_filter_stmt_catalog_public_only():
    stmt = article_service._article_filter_stmt(public_only=True, viewer_user_id=str(uuid.uuid4()))
    sql = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "directory_status" in sql.lower() or "journals" in sql.lower()


def test_article_filter_stmt_owner_with_journal_id_allows_created_by():
    owner = uuid.uuid4()
    jid = uuid.uuid4()
    stmt = article_service._article_filter_stmt(
        public_only=True,
        journal_id=jid,
        viewer_user_id=owner,
    )
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "created_by" in compiled.lower()
    assert "public" in compiled.lower()


@pytest.mark.asyncio
async def test_can_subscribe_public_ok():
    from app.services import subscriptions as sub_service

    jid = uuid.uuid4()
    uid = uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result_one(("public", None)))
    assert await sub_service.can_subscribe(session, uid, jid) is True


@pytest.mark.asyncio
async def test_can_subscribe_private_owner_ok_stranger_no():
    from app.services import subscriptions as sub_service

    jid = uuid.uuid4()
    owner = uuid.uuid4()
    stranger = uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result_one(("private", owner)))
    assert await sub_service.can_subscribe(session, owner, jid) is True
    assert await sub_service.can_subscribe(session, stranger, jid) is False
