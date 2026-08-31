from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.article import ArticleOut, ArticlesResponse
from app.services import articles as article_service

router = APIRouter(prefix="/api/v1", tags=["articles"])


@router.get("/articles", response_model=ArticlesResponse)
async def list_articles(
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    journal_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> ArticlesResponse:
    try:
        articles = await article_service.list_articles(
            session,
            limit=limit,
            offset=offset,
            journal_id=journal_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch articles") from exc
    return ArticlesResponse(articles=articles)


@router.get("/articles/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str,
    session: AsyncSession = Depends(get_session),
) -> ArticleOut:
    try:
        article = await article_service.get_article(session, article_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch article") from exc
    if article is None:
        raise HTTPException(status_code=404, detail="article not found")
    return article


@router.get("/my/feed", response_model=ArticlesResponse)
async def my_feed(
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ArticlesResponse:
    try:
        articles = await article_service.list_feed_for_user(
            session,
            user_id,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch articles") from exc
    return ArticlesResponse(articles=articles)
