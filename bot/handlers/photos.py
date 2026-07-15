from __future__ import annotations

from io import BytesIO

from aiogram import F, Bot, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.engines.gemini import GeminiClient
from bot.handlers.common import answer_photo_question
from bot.router import route_photo

router = Router(name="photos")


@router.message(F.photo)
async def photo_message(
    message: Message,
    bot: Bot,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    photo = message.photo[-1]
    buffer = BytesIO()
    await bot.download(photo, destination=buffer)
    route = route_photo(message.caption)
    await answer_photo_question(message, route.prompt, buffer.getvalue(), gemini_client, db_sessionmaker)
