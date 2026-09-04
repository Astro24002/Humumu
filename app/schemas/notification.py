from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    article_id: str
    channel: str
    status: str
    error_message: str | None = None
    match_reasons: list[str] = []
    created_at: datetime
    sent_at: datetime | None = None
    article_title: str | None = None

    @field_validator("id", "user_id", "article_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)

    @field_validator("match_reasons", mode="before")
    @classmethod
    def _split_match_reasons(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
        # DB stores comma-separated reasons (journal,author,keyword)
        return [p for p in str(v).split(",") if p.strip()]


class NotificationsResponse(BaseModel):
    notifications: list[NotificationOut]
    total: int = 0
