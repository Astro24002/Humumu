from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from app.schemas.auth import has_email as email_is_real

from app.schemas.journal import (
    AdminJournalCreate,
    AdminJournalUpdate,
    JournalOut,
    JournalRequestOut,
    JournalRequestsResponse,
    JournalsResponse,
)


class AdminStatsResponse(BaseModel):
    journal_count: int
    article_count: int
    user_count: int
    pending_requests: int
    pending_directory_reviews: int = 0
    cas_category_count: int = 0
    stub_user_count: int = 0
    wechat_unbound_count: int = 0


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    push_frequency: str
    wechat_openid: str | None = None
    wechat_template_subscribed: bool = False
    is_admin: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)

    @computed_field
    @property
    def has_email(self) -> bool:
        return email_is_real(self.email)


class AdminUsersResponse(BaseModel):
    users: list[AdminUserOut]
    total: int = 0


class AdminSetAdminRequest(BaseModel):
    is_admin: bool


class ReviewRequest(BaseModel):
    status: str


class DirectoryStatusRequest(BaseModel):
    directory_status: str


class MessageResponse(BaseModel):
    message: str


# Re-exports for router convenience
__all__ = [
    "AdminStatsResponse",
    "AdminUserOut",
    "AdminUsersResponse",
    "AdminSetAdminRequest",
    "AdminJournalCreate",
    "AdminJournalUpdate",
    "DirectoryStatusRequest",
    "JournalOut",
    "JournalsResponse",
    "JournalRequestOut",
    "JournalRequestsResponse",
    "ReviewRequest",
    "MessageResponse",
]
