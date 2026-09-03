from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class CasCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    year: int
    major: str
    minor: str
    zone: int
    is_top: bool = False

    @field_validator("id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        return str(v)


class CasCategoriesResponse(BaseModel):
    categories: list[CasCategoryOut]
    years: list[int] = []


class CreateCasCategoryRequest(BaseModel):
    year: int
    major: str
    minor: str
    zone: int
    is_top: bool = False


class AttachCasCategoriesRequest(BaseModel):
    category_ids: list[str]
