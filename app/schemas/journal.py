from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _interval_to_seconds(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("fetch_interval must be seconds or timedelta")
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        # Accept plain integer strings; leave other formats to callers.
        try:
            return int(float(value))
        except ValueError as exc:
            raise ValueError(f"invalid fetch_interval: {value!r}") from exc
    raise TypeError(f"unsupported fetch_interval type: {type(value)!r}")


class JournalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    source_type: str
    source_url: str
    description: str = ""
    fetch_interval: int | None = None
    is_active: bool = True
    created_by: str | None = None
    created_at: datetime
    article_count: int | None = None
    last_article_date: datetime | None = None
    content_type: str = "journal"
    directory_status: str = "public"
    homepage_url: str = ""
    consecutive_failures: int = 0
    last_error: str | None = None
    last_success_at: datetime | None = None
    health_status: str | None = None

    @field_validator("id", "created_by", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        if v is None:
            return None
        return str(v)

    @field_validator("fetch_interval", mode="before")
    @classmethod
    def _fetch_interval_seconds(cls, v: Any) -> int | None:
        return _interval_to_seconds(v)


class JournalsResponse(BaseModel):
    journals: list[JournalOut]


class CreateJournalRequest(BaseModel):
    journal_name: str
    source_url: str


class JournalRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    journal_name: str
    source_url: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)


class JournalRequestsResponse(BaseModel):
    requests: list[JournalRequestOut]


class PreviewRequest(BaseModel):
    # Optional so missing/invalid URLs yield the Go-compatible error message in the router.
    source_url: str = ""


class PreviewItem(BaseModel):
    title: str = ""
    url: str = ""
    published: str = ""


class PreviewResponse(BaseModel):
    name: str
    source_type: str
    items: list[PreviewItem] = []


class CreateUserJournalRequest(BaseModel):
    # Optional so missing fields yield the Go-compatible error message in the router.
    source_url: str = ""
    name: str = ""
    # private (default) | apply_public
    visibility: str = "private"


class CreateUserJournalResponse(BaseModel):
    journal: JournalOut
    already_existed: bool = False


class AdminJournalCreate(BaseModel):
    name: str
    slug: str | None = None
    source_type: str = "rss"
    source_url: str
    description: str = ""
    fetch_interval: int | None = Field(
        default=None, description="Fetch interval in seconds"
    )
    is_active: bool = True


class AdminJournalUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    description: str | None = None
    fetch_interval: int | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "AdminJournalUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field required")
        return self
