from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def has_email(email: str) -> bool:
    return bool(email) and not email.endswith("@wechat.user")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class BindEmailRequest(BaseModel):
    """Logged-in user binds a real email + password (Web / any Bearer client)."""

    email: EmailStr
    password: str = Field(min_length=6)


class AuthUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    wechat_openid: str | None = None
    push_frequency: str = "daily"
    wechat_template_subscribed: bool = False
    is_admin: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)


class AuthResponse(BaseModel):
    token: str
    user: AuthUser
    has_email: bool = True
