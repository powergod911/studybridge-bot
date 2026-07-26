from __future__ import annotations

import logging

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import StudyLog
from bot.router import Engine

logger = logging.getLogger(__name__)


async def log_study_interaction(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    message: Message,
    question: str,
    engine: Engine,
    subject_tag: str | None = None,
) -> None:
    if message.from_user is None:
        logger.warning("Skipping study log because message has no from_user")
        return

    await log_study_interaction_values(
        db_sessionmaker,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        chat_id=message.chat.id,
        question=question,
        engine=engine,
        subject_tag=subject_tag,
    )


async def log_study_interaction_values(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    *,
    telegram_id: int,
    username: str | None,
    chat_id: int,
    question: str,
    engine: Engine,
    subject_tag: str | None = None,
) -> None:
    row = StudyLog(
        telegram_id=telegram_id,
        username=username,
        chat_id=chat_id,
        question=question,
        engine_used=engine.value,
        subject_tag=subject_tag,
    )

    try:
        async with db_sessionmaker() as session:
            session.add(row)
            await session.commit()
    except Exception:
        logger.exception("Failed to write study_log row")
