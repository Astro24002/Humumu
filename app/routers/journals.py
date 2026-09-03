from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_optional_user_id
from app.schemas.journal import JournalOut, JournalsResponse
from app.services import journals as journal_service

router = APIRouter(prefix="/api/v1/journals", tags=["journals"])


@router.get("", response_model=JournalsResponse)
async def list_journals(
    session: AsyncSession = Depends(get_session),
    content_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    major: str | None = Query(default=None),
    minor: str | None = Query(default=None),
    zone: int | None = Query(default=None),
    top: bool | None = Query(default=None),
    year: int | None = Query(default=None),
) -> JournalsResponse:
    try:
        journals = await journal_service.list_journals(
            session,
            content_type=content_type,
            q=q,
            major=major,
            minor=minor,
            zone=zone,
            top=top,
            year=year,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch journals") from exc
    return JournalsResponse(journals=journals)


@router.get("/{journal_id}", response_model=JournalOut)
async def get_journal(
    journal_id: str,
    session: AsyncSession = Depends(get_session),
    viewer_id: str | None = Depends(get_optional_user_id),
) -> JournalOut:
    try:
        journal = await journal_service.get_journal(
            session,
            journal_id,
            viewer_user_id=viewer_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch journal") from exc
    if journal is None:
        raise HTTPException(status_code=404, detail="journal not found")
    return journal
