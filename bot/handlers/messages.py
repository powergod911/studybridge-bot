from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.engines.deepseek import DeepSeekClient
from bot.engines.gemini import GeminiClient
from bot.handlers.common import answer_text_question
from bot.router import route_text

router = Router(name="messages")


@router.message(F.text)
async def text_message(
    message: Message,
    deepseek_client: DeepSeekClient,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    text = message.text or ""
    route = route_text(text)
    if not route.prompt:
        await message.answer("Send a study question after the command.")
        return
    await answer_text_question(message, route.prompt, route.engine, deepseek_client, gemini_client, db_sessionmaker)
