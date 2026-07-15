from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage

from bot.config import load_settings
from bot.db.session import make_sessionmaker
from bot.engines.deepseek import DeepSeekClient
from bot.engines.gemini import GeminiClient
from bot.handlers import commands, messages, photos

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    try:
        settings = load_settings()
    except RuntimeError as exc:
        logger.critical("Startup validation failed: %s", exc)
        raise SystemExit(1) from exc

    bot = Bot(token=settings.telegram_bot_token)
    storage = RedisStorage.from_url(
        settings.redis_url,
        key_builder=DefaultKeyBuilder(with_destiny=True),
    )
    dp = Dispatcher(storage=storage)

    dp.include_router(photos.router)
    dp.include_router(commands.router)
    dp.include_router(messages.router)

    await dp.start_polling(
        bot,
        started_at=datetime.now(timezone.utc),
        db_sessionmaker=make_sessionmaker(settings.postgres_dsn),
        deepseek_client=DeepSeekClient(settings.nvidia_api_key),
        gemini_client=GeminiClient(settings.gemini_api_key),
    )


if __name__ == "__main__":
    asyncio.run(main())
