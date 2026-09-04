"""My Updates feed API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.my_updates import MyUpdateItem, MyUpdatesResponse, UpdateStatusFlags
from app.services import my_updates as updates_service

router = APIRouter(prefix="/api/v1/my", tags=["my-updates"])


@router.get("/updates", response_model=MyUpdatesResponse)
async def list_my_updates(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    filter: str | None = Query(default=None, alias="filter"),
) -> MyUpdatesResponse:
    try:
        rows = await updates_service.list_my_updates(
            session,
            user_id,
            limit=limit,
            offset=offset,
            filter_name=filter,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch updates") from exc

    items: list[MyUpdateItem] = []
    for row in rows:
        status = row.get("status") or {}
        items.append(
            MyUpdateItem(
                article_id=row["article_id"],
                title=row.get("title") or "",
                authors=list(row.get("authors") or []),
                abstract=row.get("abstract") or "",
                doi=row.get("doi"),
                url=row.get("url") or "",
                original_url=row.get("original_url") or row.get("url") or "",
                publish_date=row.get("publish_date"),
                fetched_at=row.get("fetched_at"),
                journal_id=row["journal_id"],
                journal_name=row.get("journal_name") or "",
                journal_source_type=row.get("journal_source_type") or "",
                content_type=row.get("content_type") or "journal",
                reasons=list(row.get("reasons") or []),
                status=UpdateStatusFlags(
                    is_read=bool(status.get("is_read")),
                    is_starred=bool(status.get("is_starred")),
                    is_later=bool(status.get("is_later")),
                    original_clicked_at=status.get("original_clicked_at"),
                ),
            )
        )
    return MyUpdatesResponse(updates=items)
