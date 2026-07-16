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


LocationCategory = Literal[
    "관광지", "문화시설", "축제공연행사", "여행코스", "레포츠", "숙박", "쇼핑"
]


class ChatSearchIntent(BaseModel):
    """Structured interpretation used to retrieve chat reference data."""

    intent: Literal[
        "recommendation", "place_search", "place_detail", "comparison",
        "itinerary", "local_information", "smalltalk",
    ]
    search_required: bool
    resolved_query: str = Field(min_length=1, max_length=500)
    location_terms: list[str] = Field(max_length=6)
    search_terms: list[str] = Field(max_length=12)
    preferred_categories: list[LocationCategory] = Field(max_length=7)
    excluded_categories: list[LocationCategory] = Field(max_length=7)


class ChatGeneratedAnswer(BaseModel):
    """Final answer plus the reference IDs actually selected by the model."""

    answer: str = Field(min_length=1, max_length=5000)
    location_ids: list[int] = Field(max_length=10)
    post_ids: list[int] = Field(max_length=10)
