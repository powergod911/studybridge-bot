from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    engine: Literal["auto", "deepseek", "gemini"] = "auto"
    history: list[HistoryTurn] = Field(default_factory=list, max_length=10)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty")
        return cleaned


class ChatResponse(BaseModel):
    answer: str
    engine: Literal["deepseek", "gemini"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["shadow-mentor"]
    telegram: Literal["webhook", "not_configured"]
