from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import RULES_TEXT
from bot.engines.deepseek import DeepSeekClient
from bot.engines.gemini import GeminiClient
from bot.handlers.common import answer_text_question
from bot.router import Engine, strip_command

router = Router(name="commands")

HELP_TEXT = (
    "/start - greeting and routing summary\n"
    "/help - list commands and usage\n"
    "/deep <question> - force DeepSeek for maths, physics, ICT, calculations, derivations, code\n"
    "/gem <question> - force Gemini for explanations, bio, chemistry, summaries, and images\n"
    "/cancel - clear pending state\n"
    "/ping - reply with alive and uptime\n"
    "/rules - show group/bot rules"
)

START_TEXT = (
    "StudyBridge is alive.\n\n"
    "Use /deep for calculations, derivations, proofs, algorithms, and code.\n"
    "Use /gem for explanations, summaries, biology, chemistry structures, and images.\n"
    "Photos go to Gemini vision automatically."
)


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(START_TEXT)


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
) -> None:
    prompt = strip_command(message.text or "")
    if not prompt:
        await message.answer("Usage: /deep <question>")
        return
    await answer_text_question(message, prompt, Engine.DEEPSEEK, deepseek_client, gemini_client, db_sessionmaker)


@router.message(Command("gem"))
async def gem(
    message: Message,
    deepseek_client: DeepSeekClient,
    gemini_client: GeminiClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    prompt = strip_command(message.text or "")
    if not prompt:
        await message.answer("Usage: /gem <question>")
        return
    await answer_text_question(message, prompt, Engine.GEMINI, deepseek_client, gemini_client, db_sessionmaker)
