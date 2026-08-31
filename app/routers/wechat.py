from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.wechat import (
    TemplateIDsResponse,
    TemplateSettingResponse,
    UpdateTemplateSettingRequest,
)
from app.services import users as user_service

router = APIRouter(prefix="/api/v1/wechat", tags=["wechat"])


@router.get("/template-ids", response_model=TemplateIDsResponse)
async def get_template_ids(
    user_id: str = Depends(get_current_user_id),
) -> TemplateIDsResponse:
    settings = get_settings()
    ids = [
        tid
        for tid in (settings.wechat_template_realtime, settings.wechat_template_daily)
        if tid
    ]
    return TemplateIDsResponse(template_ids=ids)


@router.get("/template-setting", response_model=TemplateSettingResponse)
async def get_template_setting(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TemplateSettingResponse:
    try:
        subscribed = await user_service.get_template_setting(session, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="server error") from exc
    return TemplateSettingResponse(subscribed=subscribed)


@router.put("/template-setting", response_model=TemplateSettingResponse)
async def update_template_setting(
    body: UpdateTemplateSettingRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TemplateSettingResponse:
    try:
        await user_service.update_template_setting(session, user_id, body.subscribed)
        await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="server error") from exc
    return TemplateSettingResponse(subscribed=body.subscribed)
