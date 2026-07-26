from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import Conversation, ConversationMessage
from bot.prompts import ChatTurn
from bot.router import Engine
from web.schemas import (
    ConversationDetail,
    ConversationMessageResponse,
    ConversationSummary,
)

MAX_CONVERSATIONS = 50
MODEL_HISTORY_TURNS = 16


class ConversationNotFoundError(LookupError):
    pass


def build_conversation_title(message: str, *, has_image: bool = False) -> str:
    cleaned = re.sub(r"\s+", " ", message).strip()
    default = "Study image" if has_image else "New conversation"
    if not cleaned:
        return default
    if cleaned == "Explain this image step-by-step." and has_image:
        return default
    return cleaned if len(cleaned) <= 54 else f"{cleaned[:51].rstrip()}..."


async def ensure_conversation(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    telegram_id: int,
    conversation_id: UUID | None,
    first_message: str,
    has_image: bool = False,
) -> UUID:
    async with sessionmaker() as session:
        if conversation_id is not None:
            owned = await session.scalar(
                select(Conversation.id).where(
                    Conversation.id == conversation_id,
                    Conversation.telegram_id == telegram_id,
                )
            )
            if owned is None:
                raise ConversationNotFoundError
            return owned

        new_id = uuid4()
        session.add(
            Conversation(
                id=new_id,
                telegram_id=telegram_id,
                title=build_conversation_title(first_message, has_image=has_image),
            )
        )
        await session.commit()
        return new_id


async def model_history(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    telegram_id: int,
    conversation_id: UUID,
) -> tuple[list[ChatTurn], Engine | None]:
    async with sessionmaker() as session:
        owned = await session.scalar(
            select(Conversation.id).where(
                Conversation.id == conversation_id,
                Conversation.telegram_id == telegram_id,
            )
        )
        if owned is None:
            raise ConversationNotFoundError

        rows = (
            await session.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
                .limit(MODEL_HISTORY_TURNS)
            )
        ).all()

    ordered = list(reversed(rows))
    history: list[ChatTurn] = [
        {"role": row.role, "content": row.content[:6000]}  # type: ignore[typeddict-item]
        for row in ordered
        if row.role in {"user", "assistant"} and row.content.strip()
    ]
    last_engine = next(
        (
            Engine(row.engine_used)
            for row in rows
            if row.role == "assistant" and row.engine_used in {"deepseek", "gemini"}
        ),
        None,
    )
    return history, last_engine


async def append_message(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    conversation_id: UUID,
    role: str,
    content: str,
    engine: Engine | None = None,
    has_image: bool = False,
) -> None:
    async with sessionmaker() as session:
        session.add(
            ConversationMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                engine_used=engine.value if engine else None,
                has_image=has_image,
            )
        )
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await session.commit()


async def list_conversations(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    telegram_id: int,
) -> list[ConversationSummary]:
    async with sessionmaker() as session:
        rows = (
            await session.scalars(
                select(Conversation)
                .where(Conversation.telegram_id == telegram_id)
                .order_by(Conversation.updated_at.desc())
                .limit(MAX_CONVERSATIONS)
            )
        ).all()
    return [
        ConversationSummary(id=row.id, title=row.title, updated_at=row.updated_at)
        for row in rows
    ]


async def get_conversation(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    telegram_id: int,
    conversation_id: UUID,
) -> ConversationDetail:
    async with sessionmaker() as session:
        conversation = await session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.telegram_id == telegram_id,
            )
        )
        if conversation is None:
            raise ConversationNotFoundError
        messages = (
            await session.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.created_at, ConversationMessage.id)
            )
        ).all()

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        updated_at=conversation.updated_at,
        messages=[
            ConversationMessageResponse(
                id=row.id,
                role=row.role,  # type: ignore[arg-type]
                content=row.content,
                engine=row.engine_used,  # type: ignore[arg-type]
                has_image=row.has_image,
                created_at=row.created_at,
            )
            for row in messages
        ],
    )


async def delete_conversation(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    telegram_id: int,
    conversation_id: UUID,
) -> None:
    async with sessionmaker() as session:
        result = await session.execute(
            delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.telegram_id == telegram_id,
            )
        )
        if result.rowcount == 0:
            raise ConversationNotFoundError
        await session.commit()
