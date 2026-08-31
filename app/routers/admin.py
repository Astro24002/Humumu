"""Admin APIs — JWT required, no RBAC (matches Go)."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.admin import (
    AdminJournalCreate,
    AdminJournalUpdate,
    AdminStatsResponse,
    AdminUserOut,
    AdminUsersResponse,
    JournalOut,
    JournalRequestsResponse,
    JournalsResponse,
    MessageResponse,
    ReviewRequest,
)
from app.services import articles as article_service
from app.services import journals as journal_service
from app.services import users as user_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_VALID_REVIEW_STATUSES = frozenset({"approved", "rejected"})


@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(
    _user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AdminStatsResponse:
    try:
        journal_count = await journal_service.count_journals(session)
        article_count = await article_service.count_articles(session)
        user_count = await user_service.count_users(session)
        pending_requests = await journal_service.count_pending_requests(session)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch stats") from exc
    return AdminStatsResponse(
        journal_count=journal_count,
        article_count=article_count,
        user_count=user_count,
        pending_requests=pending_requests,
    )


@router.get("/journals", response_model=JournalsResponse)
async def admin_list_journals(
    _user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> JournalsResponse:
    try:
        journals = await journal_service.list_journals(session)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch journals") from exc
    return JournalsResponse(journals=journals)


@router.post("/journals", response_model=JournalOut, status_code=201)
async def admin_create_journal(
    body: AdminJournalCreate,
    _user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> JournalOut:
    slug = (body.slug or "").strip() or None
    fetch_interval = (
        timedelta(seconds=body.fetch_interval) if body.fetch_interval is not None else None
    )
    try:
        journal = await journal_service.create_journal(
            session,
            name=body.name,
            source_url=body.source_url,
            source_type=body.source_type or "rss",
            description=body.description or "",
            fetch_interval=fetch_interval,
            slug=slug,
            is_active=body.is_active,
        )
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to create journal") from exc
    return journal


@router.put("/journals/{journal_id}", response_model=MessageResponse)
async def admin_update_journal(
    journal_id: str,
    body: AdminJournalUpdate,
    _user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    fields = body.model_dump(exclude_unset=True)
    if "fetch_interval" in fields and fields["fetch_interval"] is not None:
        fields["fetch_interval"] = timedelta(seconds=int(fields["fetch_interval"]))
    try:
        updated = await journal_service.update_journal(session, journal_id, **fields)
        if not updated:
            # Go still returns "updated" even if no row matched; keep soft success.
            pass
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update journal") from exc
    return MessageResponse(message="updated")


@router.delete("/journals/{journal_id}", response_model=MessageResponse)
async def admin_delete_journal(
    journal_id: str,
    _user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await journal_service.delete_journal(session, journal_id)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to delete journal") from exc
    return MessageResponse(message="deleted")


@router.get("/requests", response_model=JournalRequestsResponse)
async def admin_list_requests(
    _user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> JournalRequestsResponse:
    try:
        reqs = await journal_service.list_all_journal_requests(session)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch requests") from exc
    return JournalRequestsResponse(requests=reqs)


@router.put("/requests/{request_id}", response_model=MessageResponse)
async def admin_review_request(
    request_id: str,
    body: ReviewRequest,
    _user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    status = (body.status or "").strip()
    if status not in _VALID_REVIEW_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="status must be one of: approved, rejected",
        )
    try:
        await journal_service.update_request_status(session, request_id, status)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update request") from exc
    return MessageResponse(message=f"request {status}")


@router.get("/users", response_model=AdminUsersResponse)
async def admin_list_users(
    _user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AdminUsersResponse:
    try:
        users = await user_service.list_all_users(session)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch users") from exc
    return AdminUsersResponse(users=[AdminUserOut.model_validate(u) for u in users])
