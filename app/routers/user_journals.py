"""User self-service RSS journal preview and create."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.journal import (
    CreateUserJournalRequest,
    CreateUserJournalResponse,
    PreviewItem,
    PreviewRequest,
    PreviewResponse,
)
from app.services import journals as journal_service
from app.services import subscriptions as sub_service
from app.services.fetcher_meta import fetch_feed_meta
from app.services.url_safety import UnsafeURLError, validate_public_http_url

router = APIRouter(prefix="/api/v1/my/journals", tags=["user-journals"])

_PREPRINT_HOST_MARKERS = (
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
)


def _infer_content_type(source_url: str) -> str:
    host = (source_url or "").lower()
    if any(m in host for m in _PREPRINT_HOST_MARKERS):
        return "preprint"
    return "journal"


def _directory_status_for_visibility(visibility: str) -> str:
    v = (visibility or "private").strip().lower()
    if v == "apply_public":
        return "pending_review"
    return "private"


@router.post("/preview", response_model=PreviewResponse)
async def preview_feed(body: PreviewRequest) -> PreviewResponse:
    source_url = (body.source_url or "").strip()
    try:
        validate_public_http_url(source_url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail="valid source_url is required") from exc

    try:
        meta = await fetch_feed_meta(source_url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail="valid source_url is required") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="cannot fetch feed from this URL"
        ) from exc

    items_raw = meta.get("items") or []
    items = [
        PreviewItem(
            title=str(it.get("title") or ""),
            url=str(it.get("url") or ""),
            published=str(it.get("published") or ""),
        )
        for it in items_raw
        if isinstance(it, dict)
    ]
    return PreviewResponse(
        name=meta.get("name") or meta.get("title") or "",
        source_type=meta.get("source_type") or "rss",
        items=items,
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
    if not name:
        raise HTTPException(status_code=400, detail="name and source_url are required")
    try:
        validate_public_http_url(source_url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail="name and source_url are required") from exc

    visibility = getattr(body, "visibility", None) or "private"
    directory_status = _directory_status_for_visibility(str(visibility))
    content_type = _infer_content_type(source_url)

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
            content_type=content_type,
            directory_status=directory_status,
        )
        await sub_service.subscribe_journal(session, user_id, journal.id)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to create journal") from exc

    response.status_code = 201
    return CreateUserJournalResponse(journal=journal, already_existed=False)
