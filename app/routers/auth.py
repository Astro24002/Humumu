from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.schemas.auth import (
    AuthResponse,
    AuthUser,
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
                push_frequency="realtime",
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

    try:
        await user_service.link_wechat(session, user.id, openid)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=500, detail="server error") from None

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
