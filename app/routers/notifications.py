from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.notification import NotificationsResponse
from app.services import subscriptions as sub_service

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get("/notifications", response_model=NotificationsResponse)
async def list_notifications(
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    status: str | None = Query(default=None, description="pending | sent | failed"),
    channel: str | None = Query(default=None, description="email | wechat"),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> NotificationsResponse:
    try:
        notifications, total = await sub_service.list_notifications(
            session,
            user_id,
            limit=limit,
            offset=offset,
            status=status,
            channel=channel,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to fetch notifications") from exc
    return NotificationsResponse(notifications=notifications, total=total)
