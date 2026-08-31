from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.journal import JournalOut


class JournalSubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    journal_id: str
    created_at: datetime

    @field_validator("user_id", "journal_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)


class AuthorTrackingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    author_name: str
    created_at: datetime

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)


class KeywordSubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    keyword: str
    created_at: datetime

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)


class AuthorTrackingRequest(BaseModel):
    author_name: str


class KeywordSubscriptionRequest(BaseModel):
    keyword: str


class UpdatePushFrequencyRequest(BaseModel):
    push_frequency: str


class SubscribedJournalsResponse(BaseModel):
    journals: list[JournalOut]


class AuthorsResponse(BaseModel):
    authors: list[AuthorTrackingOut]


class KeywordsResponse(BaseModel):
    keywords: list[KeywordSubscriptionOut]
