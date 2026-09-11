from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import get_current_user_id
from app.schemas.auth import (
    AuthResponse,
    AuthUser,
    BindEmailRequest,
    LoginRequest,
    RegisterRequest,
    has_email,
)
from app.schemas.wechat import BindAccountRequest, WeChatLoginRequest
from app.services.auth_tokens import create_access_token
from app.services.password import hash_password, verify_password
from app.services import users as user_service
from app.services.wechat_api import WeChatAPIError, code_to_openid

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class MeResponse(BaseModel):
    user: AuthUser
    has_email: bool = True


def _auth_response(user, token: str) -> AuthResponse:
    return AuthResponse(
        token=token,
        user=AuthUser.model_validate(user),
        has_email=has_email(user.email),
    )


async def _openid_from_code(code: str) -> str:
    settings = get_settings()
    try:
        return await code_to_openid(settings.wechat_appid, settings.wechat_secret, code)
    except WeChatAPIError as exc:
        raise HTTPException(status_code=502, detail="wechat login failed") from exc


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    existing = await user_service.get_by_email(session, body.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="email already registered")

    password_hash = hash_password(body.password)
    try:
        user = await user_service.create_user(
            session,
            email=body.email,
            password_hash=password_hash,
            name=body.name or "",
        )
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="email already registered") from None

    settings = get_settings()
    token = create_access_token(str(user.id), user.email, settings.jwt_secret)
    return _auth_response(user, token)


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    user = await user_service.get_by_email(session, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")

    settings = get_settings()
    token = create_access_token(str(user.id), user.email, settings.jwt_secret)
    return _auth_response(user, token)


@router.get("/me", response_model=MeResponse)
async def me(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    user = await user_service.get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return MeResponse(
        user=AuthUser.model_validate(user),
        has_email=has_email(user.email),
    )


@router.post("/wechat", response_model=AuthResponse)
async def wechat_login(
    body: WeChatLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    openid = await _openid_from_code(body.code)

    user = await user_service.get_by_wechat_openid(session, openid)
    if user is None:
        try:
            user = await user_service.create_user(
                session,
                email=f"{openid}@wechat.user",
                password_hash="",
                name="WeChat User",
                wechat_openid=openid,
                push_frequency="daily",
            )
            await session.commit()
            await session.refresh(user)
        except IntegrityError:
            await session.rollback()
            # Race: another request created the stub; re-fetch
            user = await user_service.get_by_wechat_openid(session, openid)
            if user is None:
                raise HTTPException(status_code=500, detail="failed to create user") from None

    settings = get_settings()
    token = create_access_token(str(user.id), user.email, settings.jwt_secret)
    return _auth_response(user, token)


@router.post("/bind-account", response_model=AuthResponse)
async def bind_account(
    body: BindAccountRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    openid = await _openid_from_code(body.code)

    user = await user_service.get_by_email(session, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")

    existing_wx = await user_service.get_by_wechat_openid(session, openid)
    if existing_wx is not None and str(existing_wx.id) == str(user.id):
        settings = get_settings()
        token = create_access_token(str(user.id), user.email, settings.jwt_secret)
        return _auth_response(user, token)
    if existing_wx is not None:
        raise HTTPException(
            status_code=409, detail="wechat already bound to another account"
        )
    if user.wechat_openid and user.wechat_openid != openid:
        raise HTTPException(
            status_code=409, detail="account already bound to another wechat"
        )

    try:
        await user_service.link_wechat(session, user.id, openid)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="wechat already bound to another account"
        ) from None

    user = await user_service.get_by_id(session, user.id)
    if user is None:
        raise HTTPException(status_code=500, detail="server error")

    settings = get_settings()
    token = create_access_token(str(user.id), user.email, settings.jwt_secret)
    return AuthResponse(
        token=token,
        user=AuthUser.model_validate(user),
        has_email=True,
    )


@router.post("/bind-email", response_model=AuthResponse)
async def bind_email(
    body: BindEmailRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """Attach email+password to the current user (typically a WeChat stub account).

    Does not require a WeChat code — suitable for Web Settings. Rejects if the
    account already has a real email, or if the target email is taken.
    """
    user = await user_service.get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    if has_email(user.email):
        raise HTTPException(status_code=409, detail="email already bound")

    existing = await user_service.get_by_email(session, body.email)
    if existing is not None and str(existing.id) != str(user.id):
        raise HTTPException(status_code=409, detail="email already registered")

    password_hash = hash_password(body.password)
    try:
        updated = await user_service.bind_email(
            session, user_id, email=body.email, password_hash=password_hash
        )
        if updated is None:
            raise HTTPException(status_code=401, detail="invalid or expired token")
        await session.commit()
        await session.refresh(updated)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="email already registered") from None

    settings = get_settings()
    token = create_access_token(str(updated.id), updated.email, settings.jwt_secret)
    return AuthResponse(
        token=token,
        user=AuthUser.model_validate(updated),
        has_email=True,
    )
