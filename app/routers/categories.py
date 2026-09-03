"""Public CAS category facet listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.category import CasCategoriesResponse
from app.services import categories as cat_service

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("/cas", response_model=CasCategoriesResponse)
async def list_cas_categories(
    year: int | None = Query(default=None),
    major: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> CasCategoriesResponse:
    try:
        cats = await cat_service.list_categories(session, year=year, major=major)
        years = await cat_service.list_years(session)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch categories") from exc
    return CasCategoriesResponse(categories=cats, years=years)
