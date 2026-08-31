from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.common import MessageResponse
from app.schemas.subscription import UpdatePushFrequencyRequest
from app.services import users as user_service
from app.services.users import VALID_PUSH_FREQUENCIES

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.put("/push-frequency", response_model=MessageResponse)
async def update_push_frequency(
    body: UpdatePushFrequencyRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    if body.push_frequency not in VALID_PUSH_FREQUENCIES:
        raise HTTPException(
            status_code=400,
            detail="push_frequency must be one of: realtime, daily",
        )

    try:
        await user_service.update_push_frequency(session, user_id, body.push_frequency)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update settings") from exc
    return MessageResponse(message="settings updated")
