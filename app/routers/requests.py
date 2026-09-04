"""User journal-request endpoints (static /journals/requests paths)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.journal import (
    CreateJournalRequest,
    JournalRequestOut,
    JournalRequestsResponse,
)
from app.services import journals as journal_service

# Dedicated router with full paths so /journals/requests is not swallowed by /{journal_id}.
router = APIRouter(prefix="/api/v1", tags=["requests"])


@router.post(
    "/journals/requests",
    response_model=JournalRequestOut,
    status_code=201,
)
async def create_journal_request(
    body: CreateJournalRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> JournalRequestOut:
    name = (body.journal_name or "").strip()
    url = (body.source_url or "").strip()
    if not name or not url:
        raise HTTPException(status_code=400, detail="journal_name and source_url are required")

    try:
        jr = await journal_service.create_journal_request(
            session,
            user_id=user_id,
            journal_name=name,
            source_url=url,
        )
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to create request") from exc
    return jr


@router.get("/journals/requests", response_model=JournalRequestsResponse)
async def list_journal_requests(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> JournalRequestsResponse:
    try:
        reqs = await journal_service.list_journal_requests_by_user(session, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch requests") from exc
    return JournalRequestsResponse(requests=reqs, total=len(reqs))
