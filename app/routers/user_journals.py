"""User self-service RSS journal preview and create."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.journal import (
    CreateUserJournalRequest,
    CreateUserJournalResponse,
    PreviewRequest,
    PreviewResponse,
)
from app.services import journals as journal_service
from app.services import subscriptions as sub_service
from app.services.fetcher_meta import fetch_feed_meta

router = APIRouter(prefix="/api/v1/my/journals", tags=["user-journals"])


def _is_valid_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


@router.post("/preview", response_model=PreviewResponse)
async def preview_feed(body: PreviewRequest) -> PreviewResponse:
    source_url = (body.source_url or "").strip()
    if not source_url or not _is_valid_http_url(source_url):
        raise HTTPException(status_code=400, detail="valid source_url is required")

    try:
        meta = await fetch_feed_meta(source_url)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="cannot fetch feed from this URL"
        ) from exc

    return PreviewResponse(
        name=meta.get("name") or meta.get("title") or "",
        source_type=meta.get("source_type") or "rss",
    )


@router.post("", response_model=CreateUserJournalResponse, status_code=201)
async def create_my_journal(
    body: CreateUserJournalRequest,
    response: Response,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> CreateUserJournalResponse:
    name = (body.name or "").strip()
    source_url = (body.source_url or "").strip()
    if not name or not source_url or not _is_valid_http_url(source_url):
        raise HTTPException(status_code=400, detail="name and source_url are required")

    try:
        existing = await journal_service.find_by_url(session, source_url)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="failed to check existing journal"
        ) from exc

    if existing is not None:
        try:
            await sub_service.subscribe_journal(session, user_id, existing.id)
            await session.commit()
        except Exception as exc:
            raise HTTPException(status_code=500, detail="failed to subscribe") from exc
        response.status_code = 200
        return CreateUserJournalResponse(journal=existing, already_existed=True)

    try:
        journal = await journal_service.create_journal(
            session,
            name=name,
            source_url=source_url,
            created_by=user_id,
            source_type="rss",
        )
        await sub_service.subscribe_journal(session, user_id, journal.id)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to create journal") from exc

    response.status_code = 201
    return CreateUserJournalResponse(journal=journal, already_existed=False)
