"""Unit tests for categories.count_categories."""

from __future__ import annotations

import pytest

from app.services import categories as cat_service


class _CountResult:
    def __init__(self, value: int | None) -> None:
        self._value = value

    def scalar_one(self) -> int | None:
        return self._value


class _Session:
    def __init__(self, value: int | None) -> None:
        self.value = value
        self.executed = False

    async def execute(self, statement):  # noqa: ANN001
        self.executed = True
        return _CountResult(self.value)


@pytest.mark.asyncio
async def test_count_categories_returns_int():
    session = _Session(24)
    n = await cat_service.count_categories(session)
    assert n == 24
    assert session.executed is True


@pytest.mark.asyncio
async def test_count_categories_none_is_zero():
    session = _Session(None)
    n = await cat_service.count_categories(session)
    assert n == 0
