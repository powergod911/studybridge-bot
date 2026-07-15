from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

RULES_TEXT = (
    "StudyBridge group rules:\n"
    "1. Ask clear A/L study questions with enough context.\n"
    "2. Use /deep for calculations, derivations, proofs, algorithms, and code.\n"
    "3. Use /gem for explanations, summaries, biology, chemistry structures, and images.\n"
    "4. Do not post personal data, exam leaks, or copyrighted answer-book scans.\n"
    "5. Treat AI answers as study help; verify final exam answers with your teacher or marking scheme."
)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    gemini_api_key: str
    nvidia_api_key: str
    postgres_dsn: str
    redis_url: str


def load_settings() -> Settings:
    load_dotenv()

    missing = [
        name
        for name in ("TELEGRAM_BOT_TOKEN", "GEMINI_API_KEY", "NVIDIA_API_KEY")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

    return Settings(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        nvidia_api_key=os.environ["NVIDIA_API_KEY"],
        postgres_dsn=os.environ.get(
            "POSTGRES_DSN",
            "postgresql+asyncpg://studybridge_user:PASSWORD@postgres:5432/studybridge",
        ),
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/2"),
    )
