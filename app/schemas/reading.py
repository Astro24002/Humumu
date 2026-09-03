from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ArticleStatusUpdate(BaseModel):
    is_read: bool | None = None
    is_starred: bool | None = None
    is_later: bool | None = None


class ArticleStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    article_id: str
    is_read: bool = False
    is_starred: bool = False
    is_later: bool = False
    original_clicked_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("user_id", "article_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)
