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
    created_at: datetime
    sent_at: datetime | None = None

    @field_validator("id", "user_id", "article_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)


class NotificationsResponse(BaseModel):
    notifications: list[NotificationOut]
