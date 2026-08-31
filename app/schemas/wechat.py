from pydantic import BaseModel, EmailStr, Field


class WeChatLoginRequest(BaseModel):
    code: str


class BindAccountRequest(BaseModel):
    code: str
    email: EmailStr
    password: str = Field(min_length=6)


class TemplateIDsResponse(BaseModel):
    template_ids: list[str]


class TemplateSettingResponse(BaseModel):
    subscribed: bool


class UpdateTemplateSettingRequest(BaseModel):
    subscribed: bool
