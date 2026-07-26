from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

RULES_TEXT = (
    "Shadow Mentor study rules:\n"
    "1. Ask clear A/L study questions with enough context.\n"
    "2. Use /deep for calculations, derivations, proofs, algorithms, and code.\n"
    "3. Use /gem for explanations, summaries, biology, chemistry structures, and images.\n"
    "4. Do not post personal data, exam leaks, or copyrighted answer-book scans.\n"
    "5. Treat AI answers as study help; verify final exam answers with your teacher or marking scheme."
)


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _async_postgres_dsn(value: str) -> str:
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+asyncpg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)
    return value


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    gemini_api_key: str
    nvidia_api_key: str
    postgres_dsn: str
    redis_url: str
    webapp_url: str | None
    dev_mode: bool
    telegram_auth_max_age_seconds: int
    web_rate_limit_per_minute: int


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
        postgres_dsn=_async_postgres_dsn(
            os.environ.get(
                "POSTGRES_DSN",
                "postgresql+asyncpg://shadow_mentor:PASSWORD@postgres:5432/shadow_mentor",
            )
        ),
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/2"),
        webapp_url=os.environ.get("WEBAPP_URL", "").strip().rstrip("/") or None,
        dev_mode=_as_bool(os.environ.get("SHADOW_MENTOR_DEV_MODE")),
        telegram_auth_max_age_seconds=int(os.environ.get("TELEGRAM_AUTH_MAX_AGE_SECONDS", "86400")),
        web_rate_limit_per_minute=int(os.environ.get("WEB_RATE_LIMIT_PER_MINUTE", "12")),
    )
