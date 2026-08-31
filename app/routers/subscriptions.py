from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.common import MessageResponse
from app.schemas.subscription import (
    AuthorTrackingRequest,
    AuthorsResponse,
    KeywordSubscriptionRequest,
    KeywordsResponse,
    SubscribedJournalsResponse,
)
from app.services import subscriptions as sub_service

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


@router.get("/journals", response_model=SubscribedJournalsResponse)
async def list_subscribed_journals(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SubscribedJournalsResponse:
    try:
        journals = await sub_service.list_subscribed_journals(session, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch subscriptions") from exc
    return SubscribedJournalsResponse(journals=journals)


@router.post("/journals/{journal_id}", response_model=MessageResponse)
async def subscribe_journal(
    journal_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        exists = await sub_service.journal_exists(session, journal_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to subscribe") from exc
    if not exists:
        raise HTTPException(status_code=404, detail="journal not found")

    try:
        await sub_service.subscribe_journal(session, user_id, journal_id)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to subscribe") from exc
    return MessageResponse(message="subscribed")


@router.delete("/journals/{journal_id}", response_model=MessageResponse)
async def unsubscribe_journal(
    journal_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await sub_service.unsubscribe_journal(session, user_id, journal_id)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to unsubscribe") from exc
    return MessageResponse(message="unsubscribed")


@router.get("/authors", response_model=AuthorsResponse)
async def list_authors(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AuthorsResponse:
    try:
        authors = await sub_service.list_authors(session, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch authors") from exc
    return AuthorsResponse(authors=authors)


@router.post("/authors", response_model=MessageResponse, status_code=201)
async def add_author(
    body: AuthorTrackingRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await sub_service.add_author(session, user_id, body.author_name)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to add author") from exc
    return MessageResponse(message="author added")


@router.delete("/authors/{author_id}", response_model=MessageResponse)
async def remove_author(
    author_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await sub_service.remove_author(session, author_id, user_id)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to remove author") from exc
    return MessageResponse(message="author removed")


@router.get("/keywords", response_model=KeywordsResponse)
async def list_keywords(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> KeywordsResponse:
    try:
        keywords = await sub_service.list_keywords(session, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch keywords") from exc
    return KeywordsResponse(keywords=keywords)


@router.post("/keywords", response_model=MessageResponse, status_code=201)
async def add_keyword(
    body: KeywordSubscriptionRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await sub_service.add_keyword(session, user_id, body.keyword)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to add keyword") from exc
    return MessageResponse(message="keyword added")


@router.delete("/keywords/{keyword_id}", response_model=MessageResponse)
async def remove_keyword(
    keyword_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    try:
        await sub_service.remove_keyword(session, keyword_id, user_id)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to remove keyword") from exc
    return MessageResponse(message="keyword removed")
