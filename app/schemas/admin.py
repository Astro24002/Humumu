from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

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


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    push_frequency: str
    wechat_openid: str | None = None
    wechat_template_subscribed: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)


class AdminUsersResponse(BaseModel):
    users: list[AdminUserOut]


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
