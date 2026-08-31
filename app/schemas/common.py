from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    message: str


class ErrorBody(BaseModel):
    error: str


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
