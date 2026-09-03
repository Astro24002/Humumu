"""Reading status APIs: read / star / later / original-click."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.common import MessageResponse
from app.schemas.reading import ArticleStatusOut, ArticleStatusUpdate
from app.services import reading_status as reading_service

router = APIRouter(prefix="/api/v1/my/articles", tags=["reading"])


@router.get("/{article_id}/status", response_model=ArticleStatusOut)
async def get_article_status(
    article_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ArticleStatusOut:
    try:
        status = await reading_service.get_status(session, user_id, article_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch status") from exc
    if status is None:
        return ArticleStatusOut(
            user_id=user_id,
            article_id=article_id,
            is_read=False,
            is_starred=False,
            is_later=False,
        )
    return status


@router.put("/{article_id}/status", response_model=ArticleStatusOut)
async def update_article_status(
    article_id: str,
    body: ArticleStatusUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ArticleStatusOut:
    if body.is_read is None and body.is_starred is None and body.is_later is None:
        raise HTTPException(status_code=400, detail="at least one status field required")
    try:
        status = await reading_service.upsert_status(
            session,
            user_id,
            article_id,
            is_read=body.is_read,
            is_starred=body.is_starred,
            is_later=body.is_later,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update status") from exc
    return status


@router.post("/{article_id}/original-click", response_model=MessageResponse)
async def original_click(
    article_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await reading_service.mark_original_click(session, user_id, article_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to record click") from exc
    return MessageResponse(message="recorded")
