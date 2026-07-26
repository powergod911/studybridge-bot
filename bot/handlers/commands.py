from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import RULES_TEXT, Settings
from bot.engines.deepseek import DeepSeekClient
from bot.engines.gemini import GeminiClient
from bot.handlers.common import answer_text_question
from bot.router import Engine, strip_command

router = Router(name="commands")

HELP_TEXT = (
    "/start - greeting and routing summary\n"
    "/app - open the Shadow Mentor Mini App\n"
    "/help - list commands and usage\n"
    "/deep <question> - force DeepSeek for maths, physics, ICT, calculations, derivations, code\n"
    "/gem <question> - force Gemini for explanations, bio, chemistry, summaries, and images\n"
    "/cancel - clear pending state\n"
    "/ping - reply with alive and uptime\n"
    "/rules - show group/bot rules"
)

START_TEXT = (
    "Shadow Mentor is ready.\n\n"
    "Use /deep for calculations, derivations, proofs, algorithms, and code.\n"
    "Use /gem for explanations, summaries, biology, chemistry structures, and images.\n"
    "Photos go to Gemini vision automatically.\n"
    "For beautifully rendered equations and a full chat interface, open the study app."
)


def web_app_markup(settings: Settings) -> InlineKeyboardMarkup | None:
    if not settings.webapp_url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Shadow Mentor",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )


@router.message(Command("start"))
async def start(message: Message, settings: Settings) -> None:
    markup = web_app_markup(settings) if message.chat.type == ChatType.PRIVATE else None
    await message.answer(START_TEXT, reply_markup=markup)


@router.message(Command("app"))
async def app_command(message: Message, settings: Settings) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Open a private chat with Shadow Mentor to launch the study app.")
        return
    markup = web_app_markup(settings)
    if markup is None:
        await message.answer("The Shadow Mentor Mini App is not configured yet.")
        return
    await message.answer("Open your study workspace:", reply_markup=markup)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Pending state cleared.")


@router.message(Command("ping"))
async def ping(message: Message, started_at: datetime) -> None:
    delta = datetime.now(timezone.utc) - started_at
    seconds = int(delta.total_seconds())
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    await message.answer(f"alive - uptime {hours}h {minutes}m {seconds}s")


@router.message(Command("rules"))
async def rules(message: Message) -> None:
    await message.answer(RULES_TEXT)


@router.message(Command("deep"))
async def deep(
    message: Message,
    deepseek_client: DeepSeekClient,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
    rate_limit_redis: Redis,
    settings: Settings,
) -> None:
    prompt = strip_command(message.text or "")
    if not prompt:
        await message.answer("Usage: /deep <question>")
        return
    await answer_text_question(
        message,
        prompt,
        Engine.DEEPSEEK,
        deepseek_client,
        gemini_client,
        db_sessionmaker,
        rate_limit_redis,
        settings,
    )


@router.message(Command("gem"))
async def gem(
    message: Message,
    deepseek_client: DeepSeekClient,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
    rate_limit_redis: Redis,
    settings: Settings,
) -> None:
    prompt = strip_command(message.text or "")
    if not prompt:
        await message.answer("Usage: /gem <question>")
        return
    await answer_text_question(
        message,
        prompt,
        Engine.GEMINI,
        deepseek_client,
        gemini_client,
        db_sessionmaker,
        rate_limit_redis,
        settings,
    )
