from __future__ import annotations

import logging

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.logging import log_study_interaction
from bot.engines.deepseek import DeepSeekClient
from bot.engines.errors import AIBusyError
from bot.engines.gemini import GeminiClient
from bot.router import Engine

logger = logging.getLogger(__name__)

BUSY_TEXT = "That AI's busy right now - try again in a moment."
ERROR_TEXT = "I hit an error while answering that. Try again in a moment."


def split_telegram_text(text: str, limit: int = 3900) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()
    while remaining:
        chunks.append(remaining[:limit])
        remaining = remaining[limit:]
    return chunks or ["I could not generate an answer."]


async def answer_text_question(
    message: Message,
    prompt: str,
    engine: Engine,
    deepseek_client: DeepSeekClient,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
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

    for chunk in split_telegram_text(answer):
        await message.answer(chunk)


async def answer_photo_question(
    message: Message,
    prompt: str,
    image_bytes: bytes,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
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

    for chunk in split_telegram_text(answer):
        await message.answer(chunk)
