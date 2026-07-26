from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-pro"
GEMINI_MODEL = "gemini-3.5-flash"
PHOTO_DEFAULT_PROMPT = "Explain this study diagram step-by-step."

DEEPSEEK_RE = re.compile(
    r"\b(solve|calculate|derive|prove|equation|algorithm|code|math|physics)\b"
    r"|ගණනය|විසඳ|සමීකරණ|ව්‍යුත්පන්න",
    re.IGNORECASE,
)
GEMINI_RE = re.compile(r"\b(explain|describe|summarize|what is|why)\b", re.IGNORECASE)
MATH_RE = re.compile(r"(?:\d\s*[+\-*/=^]\s*\d)|(?:[a-zA-Z]\s*=\s*[^=])")


class Engine(StrEnum):
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"


@dataclass(frozen=True)
class Route:
    engine: Engine
    prompt: str


def strip_command(text: str) -> str:
    parts = text.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def route_text(text: str) -> Route:
    stripped = text.strip()
    lowered = stripped.lower()

    if lowered.startswith("/deep"):
        return Route(engine=Engine.DEEPSEEK, prompt=strip_command(stripped))
    if lowered.startswith("/gem"):
        return Route(engine=Engine.GEMINI, prompt=strip_command(stripped))
    if DEEPSEEK_RE.search(stripped) or MATH_RE.search(stripped):
        return Route(engine=Engine.DEEPSEEK, prompt=stripped)
    if GEMINI_RE.search(stripped):
        return Route(engine=Engine.GEMINI, prompt=stripped)
    return Route(engine=Engine.GEMINI, prompt=stripped)


def route_photo(caption: str | None) -> Route:
    prompt = caption.strip() if caption and caption.strip() else PHOTO_DEFAULT_PROMPT
    return Route(engine=Engine.GEMINI, prompt=prompt)
