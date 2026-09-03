"""Service-level tests for legacy journal_request approval creating a public journal."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services import journals as journal_service


class _Req:
    def __init__(self):
        self.id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.journal_name = "New Journal"
        self.source_url = "https://example.com/feed.xml"
        self.status = "pending"
        self.reviewed_at = None


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, req):
        self.req = req
        self.flushed = False

    async def execute(self, statement):  # noqa: ANN001
        return _Result(self.req)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_approve_creates_journal_when_missing():
    req = _Req()
    session = _Session(req)
    created = SimpleNamespace(id=str(uuid.uuid4()), directory_status="public")

    with (
        patch(
            "app.services.journals.find_by_url",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_find,
        patch(
            "app.services.journals.create_journal",
            new_callable=AsyncMock,
            return_value=created,
        ) as mock_create,
        patch(
            "app.services.subscriptions.subscribe_journal",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_sub,
    ):
        ok = await journal_service.update_request_status(session, req.id, "approved")

    assert ok is True
    mock_find.assert_awaited_once()
    mock_create.assert_awaited_once()
    kwargs = mock_create.await_args.kwargs
    assert kwargs["name"] == "New Journal"
    assert kwargs["source_url"] == "https://example.com/feed.xml"
    assert kwargs["directory_status"] == "public"
    mock_sub.assert_awaited_once()
    assert req.status == "approved"
    assert req.reviewed_at is not None
    assert session.flushed is True


@pytest.mark.asyncio
async def test_approve_reuses_existing_and_promotes_public():
    req = _Req()
    session = _Session(req)
    existing = SimpleNamespace(id=str(uuid.uuid4()), directory_status="private")

    with (
        patch(
            "app.services.journals.find_by_url",
            new_callable=AsyncMock,
            return_value=existing,
        ),
        patch(
            "app.services.journals.create_journal",
            new_callable=AsyncMock,
        ) as mock_create,
        patch(
            "app.services.journals.set_directory_status",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_status,
        patch(
            "app.services.subscriptions.subscribe_journal",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        ok = await journal_service.update_request_status(session, req.id, "approved")

    assert ok is True
    mock_create.assert_not_awaited()
    mock_status.assert_awaited_once()
    assert mock_status.await_args.args[1] == existing.id
    assert mock_status.await_args.args[2] == "public"
    assert req.status == "approved"


@pytest.mark.asyncio
async def test_reject_only_updates_status():
    req = _Req()
    session = _Session(req)

    with (
        patch(
            "app.services.journals.find_by_url",
            new_callable=AsyncMock,
        ) as mock_find,
        patch(
            "app.services.journals.create_journal",
            new_callable=AsyncMock,
        ) as mock_create,
    ):
        ok = await journal_service.update_request_status(session, req.id, "rejected")

    assert ok is True
    mock_find.assert_not_awaited()
    mock_create.assert_not_awaited()
    assert req.status == "rejected"
    assert req.reviewed_at is not None
