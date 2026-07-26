from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import Settings
from bot.db.session import make_sessionmaker
from bot.engines.deepseek import DeepSeekClient
from bot.engines.gemini import GeminiClient
from bot.handlers import commands, messages, photos


def make_webhook_secret(bot_token: str) -> str:
    return hashlib.sha256(f"shadow-mentor-webhook:{bot_token}".encode()).hexdigest()


@dataclass
class BotApplication:
    settings: Settings
    bot: Bot
    dispatcher: Dispatcher
    storage: RedisStorage
    dependencies: dict[str, object]

    async def prepare(self) -> None:
        await self.bot.set_my_commands(
            [
                BotCommand(command="start", description="Open Shadow Mentor"),
                BotCommand(command="app", description="Open the study app"),
                BotCommand(command="deep", description="Maths, physics, code"),
                BotCommand(command="gem", description="Explanations and images"),
                BotCommand(command="help", description="Show available commands"),
            ]
        )
        if self.settings.webapp_url:
            await self.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Open Shadow Mentor",
                    web_app=WebAppInfo(url=self.settings.webapp_url),
                )
            )

    async def configure_webhook(self) -> None:
        if not self.settings.webapp_url:
            raise RuntimeError("WEBAPP_URL is required to configure the Telegram webhook")

        await self.prepare()
        await self.bot.set_webhook(
            url=f"{self.settings.webapp_url}/telegram/webhook",
            secret_token=make_webhook_secret(self.settings.telegram_bot_token),
            allowed_updates=self.dispatcher.resolve_used_update_types(),
            drop_pending_updates=False,
        )

    async def poll(self) -> None:
        await self.prepare()
        await self.bot.delete_webhook(drop_pending_updates=False)
        await self.dispatcher.start_polling(
            self.bot,
            close_bot_session=False,
            **self.dependencies,
        )

    async def close(self) -> None:
        await self.storage.close()
        await self.bot.session.close()


def create_bot_application(settings: Settings) -> BotApplication:
    bot = Bot(token=settings.telegram_bot_token)
    storage = RedisStorage.from_url(
        settings.redis_url,
        key_builder=DefaultKeyBuilder(with_destiny=True),
    )
    dispatcher = Dispatcher(storage=storage)
    dispatcher.include_router(photos.router)
    dispatcher.include_router(commands.router)
    dispatcher.include_router(messages.router)

    db_sessionmaker: async_sessionmaker[AsyncSession] = make_sessionmaker(settings.postgres_dsn)
    dependencies: dict[str, object] = {
        "started_at": datetime.now(timezone.utc),
        "db_sessionmaker": db_sessionmaker,
        "deepseek_client": DeepSeekClient(settings.nvidia_api_key),
        "gemini_client": GeminiClient(settings.gemini_api_key),
        "settings": settings,
        "rate_limit_redis": storage.redis,
    }
    return BotApplication(
        settings=settings,
        bot=bot,
        dispatcher=dispatcher,
        storage=storage,
        dependencies=dependencies,
    )
