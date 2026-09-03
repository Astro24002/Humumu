from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.services.auth_tokens import decode_token
from app.services import users as user_service


async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing authorization header")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="invalid authorization format")

    settings = get_settings()
    try:
        payload = decode_token(parts[1], settings.jwt_secret)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired token") from None

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return str(user_id)


async def require_admin(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> str:
    """Require a valid JWT whose user has is_admin=True. Returns user_id."""
    user_id = await get_current_user_id(authorization)
    user = await user_service.get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    if not bool(getattr(user, "is_admin", False)):
        raise HTTPException(status_code=403, detail="admin required")
    return user_id
