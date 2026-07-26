from __future__ import annotations

import logging

from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import Settings
from bot.db.logging import log_study_interaction
from bot.engines.deepseek import DeepSeekClient
from bot.engines.errors import AIBusyError
from bot.engines.gemini import GeminiClient
from bot.formatting import format_telegram_text, split_telegram_text
from bot.rate_limit import RateLimitExceeded, enforce_rate_limit
from bot.router import Engine

logger = logging.getLogger(__name__)

BUSY_TEXT = "That AI's busy right now - try again in a moment."
ERROR_TEXT = "I hit an error while answering that. Try again in a moment."
RATE_LIMIT_TEXT = "You're asking too quickly. Please wait a moment before the next question."


async def _within_rate_limit(
    message: Message,
    redis_client: Redis,
    settings: Settings,
) -> bool:
    if message.from_user is None:
        return True

    try:
        await enforce_rate_limit(
            redis_client,
            namespace="telegram",
            user_id=message.from_user.id,
            limit=settings.bot_rate_limit_per_minute,
        )
    except RateLimitExceeded:
        await message.answer(RATE_LIMIT_TEXT)
        return False
    except Exception:
        logger.exception("Telegram rate-limit check failed for user_id=%s", message.from_user.id)

    return True

async def answer_text_question(
    message: Message,
    prompt: str,
    engine: Engine,
    deepseek_client: DeepSeekClient,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
    rate_limit_redis: Redis,
    settings: Settings,
) -> None:
    if not await _within_rate_limit(message, rate_limit_redis, settings):
        return

    await log_study_interaction(db_sessionmaker, message, prompt, engine)

    try:
        if engine == Engine.DEEPSEEK:
            answer = await deepseek_client.answer(prompt)
        else:
            answer = await gemini_client.answer(prompt)
    except AIBusyError:
        logger.warning("%s failed with busy response for chat_id=%s", engine.value, message.chat.id)
        await message.answer(BUSY_TEXT)
        return
    except Exception:
        logger.exception("%s failed for chat_id=%s", engine.value, message.chat.id)
        await message.answer(ERROR_TEXT)
        return

    for chunk in split_telegram_text(format_telegram_text(answer)):
        await message.answer(chunk)


async def answer_photo_question(
    message: Message,
    prompt: str,
    image_bytes: bytes,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
    rate_limit_redis: Redis,
    settings: Settings,
) -> None:
    if not await _within_rate_limit(message, rate_limit_redis, settings):
        return

    await log_study_interaction(db_sessionmaker, message, f"{prompt} [photo]", Engine.GEMINI)

    try:
        answer = await gemini_client.answer_image(prompt, image_bytes)
    except AIBusyError:
        logger.warning("Gemini vision failed with busy response for chat_id=%s", message.chat.id)
        await message.answer(BUSY_TEXT)
        return
    except Exception:
        logger.exception("Gemini vision failed for chat_id=%s", message.chat.id)
        await message.answer(ERROR_TEXT)
        return

    for chunk in split_telegram_text(format_telegram_text(answer)):
        await message.answer(chunk)
