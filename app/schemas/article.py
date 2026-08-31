from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doi: str | None = None
    title: str
    authors: list[str] = []
    abstract: str = ""
    journal_id: str
    journal_name: str | None = None
    journal_source_type: str | None = None
    publish_date: date | datetime | None = None
    url: str = ""
    fetched_at: datetime

    @field_validator("id", "journal_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)

    @field_validator("authors", mode="before")
    @classmethod
    def _authors_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        return list(v)


class ArticlesResponse(BaseModel):
    articles: list[ArticleOut]


class ArticleWithJournal(ArticleOut):
    journal_name: str = ""
    journal_slug: str = ""
