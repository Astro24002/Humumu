from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, field_validator


class UpdateStatusFlags(BaseModel):
    is_read: bool = False
    is_starred: bool = False
    is_later: bool = False
    original_clicked_at: datetime | None = None


class MyUpdateItem(BaseModel):
    article_id: str
    title: str
    authors: list[str] = []
    abstract: str = ""
    doi: str | None = None
    url: str = ""
    original_url: str = ""
    publish_date: date | str | None = None
    fetched_at: datetime | None = None
    journal_id: str
    journal_name: str
    journal_source_type: str | None = None
    content_type: str = "journal"
    reasons: list[str] = []
    status: UpdateStatusFlags = UpdateStatusFlags()

    @field_validator("article_id", "journal_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v) if v is not None else v


class MyUpdatesResponse(BaseModel):
    updates: list[MyUpdateItem]
