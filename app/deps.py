from fastapi import Header, HTTPException

from app.config import get_settings
from app.services.auth_tokens import decode_token


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
