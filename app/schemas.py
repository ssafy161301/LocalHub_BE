from typing import Literal

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    category: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=5000)
    password: str = Field(min_length=4, max_length=20)
    locationId: int | None = None


class PasswordBody(BaseModel):
    password: str = Field(min_length=4, max_length=20)


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[HistoryItem] = Field(default_factory=list, max_length=20)
