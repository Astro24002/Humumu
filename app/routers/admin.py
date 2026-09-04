"""Admin APIs — require real admin role (users.is_admin)."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin
from app.schemas.admin import (
    AdminJournalCreate,
    AdminJournalUpdate,
    AdminSetAdminRequest,
    AdminStatsResponse,
    AdminUserOut,
    AdminUsersResponse,
    DirectoryStatusRequest,
    JournalOut,
    JournalRequestsResponse,
    JournalsResponse,
    MessageResponse,
    ReviewRequest,
)
from app.schemas.category import (
    AttachCasCategoriesRequest,
    CasCategoryOut,
    CreateCasCategoryRequest,
)
from app.services import articles as article_service
from app.services import categories as cat_service
from app.services import journals as journal_service
from app.services import users as user_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_VALID_REVIEW_STATUSES = frozenset({"approved", "rejected"})


@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(
    _user_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminStatsResponse:
    try:
        journal_count = await journal_service.count_journals(session)
        article_count = await article_service.count_articles(session)
        user_count = await user_service.count_users(session)
        pending_requests = await journal_service.count_pending_requests(session)
        pending_directory_reviews = await journal_service.count_pending_directory_reviews(
            session
        )
        cas_category_count = await cat_service.count_categories(session)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch stats") from exc
    return AdminStatsResponse(
        journal_count=journal_count,
        article_count=article_count,
        user_count=user_count,
        pending_requests=pending_requests,
        pending_directory_reviews=pending_directory_reviews,
        cas_category_count=cas_category_count,
    )


@router.get("/journals", response_model=JournalsResponse)
async def admin_list_journals(
    _user_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    content_type: str | None = Query(default=None),
    source_type: str | None = Query(
        default=None,
        description="rss | arxiv | cnki",
        pattern="^(rss|arxiv|cnki)$",
    ),
    directory_status: str | None = Query(default=None),
    sort: str | None = Query(
        default=None,
        description="name | articles | updated",
        pattern="^(name|articles|updated)$",
    ),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> JournalsResponse:
    try:
        journals, total = await journal_service.list_journals(
            session,
            public_only=False,
            q=q,
            content_type=content_type,
            source_type=source_type,
            directory_status=directory_status,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch journals") from exc
    return JournalsResponse(journals=journals, total=total)


@router.post("/journals", response_model=JournalOut, status_code=201)
async def admin_create_journal(
    body: AdminJournalCreate,
    _user_id: str = Depends(require_admin),
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
            content_type=body.content_type or "journal",
            directory_status=body.directory_status or "public",
            homepage_url=body.homepage_url or "",
        )
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to create journal") from exc
    return journal


@router.put("/journals/{journal_id}", response_model=MessageResponse)
async def admin_update_journal(
    journal_id: str,
    body: AdminJournalUpdate,
    _user_id: str = Depends(require_admin),
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
    _user_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await journal_service.delete_journal(session, journal_id)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to delete journal") from exc
    return MessageResponse(message="deleted")


@router.post("/journals/{journal_id}/directory_status", response_model=MessageResponse)
async def admin_set_directory_status(
    journal_id: str,
    body: DirectoryStatusRequest,
    _user_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        updated = await journal_service.set_directory_status(
            session, journal_id, body.directory_status
        )
        if not updated:
            raise HTTPException(status_code=404, detail="journal not found")
        await session.commit()
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update directory status") from exc
    return MessageResponse(message="directory_status updated")


@router.get("/requests", response_model=JournalRequestsResponse)
async def admin_list_requests(
    _user_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    status: str | None = Query(
        default=None,
        description="pending | approved | rejected",
        pattern="^(pending|approved|rejected)$",
    ),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> JournalRequestsResponse:
    try:
        reqs, total = await journal_service.list_all_journal_requests(
            session, status=status, limit=limit, offset=offset
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch requests") from exc
    return JournalRequestsResponse(requests=reqs, total=total)


@router.put("/requests/{request_id}", response_model=MessageResponse)
async def admin_review_request(
    request_id: str,
    body: ReviewRequest,
    _user_id: str = Depends(require_admin),
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
    _user_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminUsersResponse:
    try:
        users, total = await user_service.list_all_users(
            session, q=q, limit=limit, offset=offset
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch users") from exc
    return AdminUsersResponse(
        users=[AdminUserOut.model_validate(u) for u in users],
        total=total,
    )


@router.post("/users/{target_user_id}/admin", response_model=AdminUserOut)
async def admin_set_user_admin(
    target_user_id: str,
    body: AdminSetAdminRequest,
    actor_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminUserOut:
    """Grant or revoke is_admin. Admins cannot demote themselves (avoid lockout)."""
    if str(target_user_id) == str(actor_id) and body.is_admin is False:
        raise HTTPException(
            status_code=400,
            detail="cannot revoke your own admin role",
        )
    try:
        user = await user_service.set_admin(session, target_user_id, body.is_admin)
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        await session.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update admin role") from exc
    return AdminUserOut.model_validate(user)


@router.post("/cas/categories", response_model=CasCategoryOut, status_code=201)
async def admin_create_cas_category(
    body: CreateCasCategoryRequest,
    _user_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> CasCategoryOut:
    try:
        cat = await cat_service.create_category(
            session,
            year=body.year,
            major=body.major,
            minor=body.minor,
            zone=body.zone,
            is_top=body.is_top,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to create category") from exc
    return cat


@router.post("/journals/{journal_id}/cas", response_model=MessageResponse)
async def admin_attach_cas_categories(
    journal_id: str,
    body: AttachCasCategoriesRequest,
    _user_id: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await cat_service.attach_categories(session, journal_id, body.category_ids)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to attach categories") from exc
    return MessageResponse(message="categories attached")
