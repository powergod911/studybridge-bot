from __future__ import annotations

import hmac
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, cast
from uuid import UUID

from aiogram.types import Update
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import Settings, load_settings
from bot.db.logging import log_study_interaction_values
from bot.engines.deepseek import DeepSeekClient
from bot.engines.errors import AIBusyError
from bot.engines.gemini import GeminiClient
from bot.prompts import ChatTurn
from bot.router import Engine, route_text
from bot.runtime import BotApplication, create_bot_application, make_webhook_secret
from web.auth import TelegramUser, require_telegram_user
from web.conversations import (
    ConversationNotFoundError,
    append_message,
    delete_conversation,
    ensure_conversation,
    get_conversation,
    list_conversations,
    model_history,
)
from web.image_validation import ImageValidationError, validate_image_bytes
from web.rate_limit import enforce_rate_limit
from web.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    HealthResponse,
)

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
FOLLOW_UP_RE = re.compile(
    r"^\s*(why|how|then|next|continue|show me|what about|another|that|this|it|"
    r"can you|could you|explain that|try again|ඇයි|කොහොමද|එතකොට|ඊළඟ|තව)\b",
    re.IGNORECASE,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = load_settings()
    redis_client = cast(Redis, redis_from_url(settings.redis_url, decode_responses=True))
    await redis_client.ping()

    bot_application = create_bot_application(settings)
    app.state.settings = settings
    app.state.redis = redis_client
    app.state.bot_application = bot_application
    app.state.db_sessionmaker = bot_application.dependencies["db_sessionmaker"]
    app.state.deepseek_client = bot_application.dependencies["deepseek_client"]
    app.state.gemini_client = bot_application.dependencies["gemini_client"]

    if settings.webapp_url:
        await bot_application.configure_webhook()
        logger.info("Telegram webhook configured at %s/telegram/webhook", settings.webapp_url)
    else:
        logger.warning("WEBAPP_URL is not set; web UI is available but Telegram webhook is disabled")

    try:
        yield
    finally:
        await redis_client.aclose()
        await bot_application.close()


app = FastAPI(
    title="Shadow Mentor",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://telegram.org https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net data:; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self'; "
        "frame-ancestors https://web.telegram.org https://*.telegram.org"
    )
    return response


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    telegram_status = "webhook" if request.app.state.settings.webapp_url else "not_configured"
    return HealthResponse(status="ok", service="shadow-mentor", telegram=telegram_status)


@app.post("/telegram/webhook", include_in_schema=False)
async def telegram_webhook(request: Request) -> Response:
    application: BotApplication = request.app.state.bot_application
    expected_secret = make_webhook_secret(application.settings.telegram_bot_token)
    received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(received_secret, expected_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    update = Update.model_validate(await request.json(), context={"bot": application.bot})
    await application.dispatcher.feed_webhook_update(
        application.bot,
        update,
        **application.dependencies,
    )
    return Response(status_code=status.HTTP_200_OK)


def _history_for_engine(request: ChatRequest) -> list[ChatTurn]:
    return [
        {"role": turn.role, "content": turn.content}
        for turn in request.history
    ]


def _select_engine(
    payload: ChatRequest,
    *,
    has_history: bool,
    last_engine: Engine | None,
) -> Engine:
    if payload.engine != "auto":
        return Engine(payload.engine)
    if has_history and last_engine is not None and FOLLOW_UP_RE.search(payload.message):
        return last_engine
    return route_text(payload.message).engine


@app.get("/api/conversations", response_model=list[ConversationSummary])
async def conversation_list(
    request: Request,
    user: Annotated[TelegramUser, Depends(require_telegram_user)],
) -> list[ConversationSummary]:
    db_sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    return await list_conversations(db_sessionmaker, telegram_id=user.id)


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def conversation_detail(
    conversation_id: UUID,
    request: Request,
    user: Annotated[TelegramUser, Depends(require_telegram_user)],
) -> ConversationDetail:
    db_sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    try:
        return await get_conversation(
            db_sessionmaker,
            telegram_id=user.id,
            conversation_id=conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        ) from exc


@app.delete("/api/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def conversation_delete(
    conversation_id: UUID,
    request: Request,
    user: Annotated[TelegramUser, Depends(require_telegram_user)],
) -> Response:
    db_sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    try:
        await delete_conversation(
            db_sessionmaker,
            telegram_id=user.id,
            conversation_id=conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    user: Annotated[TelegramUser, Depends(require_telegram_user)],
) -> ChatResponse:
    settings: Settings = request.app.state.settings
    redis_client: Redis = request.app.state.redis
    await enforce_rate_limit(redis_client, user.id, settings.web_rate_limit_per_minute)

    db_sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    try:
        conversation_id = await ensure_conversation(
            db_sessionmaker,
            telegram_id=user.id,
            conversation_id=payload.conversation_id,
            first_message=payload.message,
        )
        stored_history, last_engine = await model_history(
            db_sessionmaker,
            telegram_id=user.id,
            conversation_id=conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        ) from exc

    history = stored_history or _history_for_engine(payload)
    engine = _select_engine(
        payload,
        has_history=bool(history),
        last_engine=last_engine,
    )
    await append_message(
        db_sessionmaker,
        conversation_id=conversation_id,
        role="user",
        content=payload.message,
    )
    await log_study_interaction_values(
        db_sessionmaker,
        telegram_id=user.id,
        username=user.username,
        chat_id=user.id,
        question=payload.message,
        engine=engine,
        subject_tag="mini_app",
    )

    try:
        if engine == Engine.DEEPSEEK:
            client: DeepSeekClient = request.app.state.deepseek_client
            answer = await client.answer(
                payload.message,
                channel="web",
                history=history,
            )
        else:
            client = request.app.state.gemini_client
            answer = await client.answer(
                payload.message,
                channel="web",
                history=history,
            )
    except AIBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The selected AI is busy. Please try again shortly.",
        ) from exc
    except Exception as exc:
        logger.exception("Mini App chat failed for telegram_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Shadow Mentor could not answer that question.",
        ) from exc

    await append_message(
        db_sessionmaker,
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        engine=engine,
    )
    return ChatResponse(
        answer=answer,
        engine=engine.value,
        conversation_id=conversation_id,
    )


@app.post("/api/image", response_model=ChatResponse)
async def image_question(
    request: Request,
    user: Annotated[TelegramUser, Depends(require_telegram_user)],
    image: Annotated[UploadFile, File()],
    prompt: Annotated[
        str,
        Form(min_length=1, max_length=8000),
    ] = "Explain this study image step-by-step.",
    conversation_id: Annotated[UUID | None, Form()] = None,
) -> ChatResponse:
    settings: Settings = request.app.state.settings
    redis_client: Redis = request.app.state.redis
    await enforce_rate_limit(redis_client, user.id, settings.web_rate_limit_per_minute)

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )

    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Images must be 10 MB or smaller.",
        )

    try:
        validate_image_bytes(
            image_bytes,
            declared_content_type=image.content_type,
        )
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a valid JPEG, PNG, or WebP image up to 25 megapixels.",
        ) from exc

    db_sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    try:
        active_conversation_id = await ensure_conversation(
            db_sessionmaker,
            telegram_id=user.id,
            conversation_id=conversation_id,
            first_message=prompt,
            has_image=True,
        )
        history, _ = await model_history(
            db_sessionmaker,
            telegram_id=user.id,
            conversation_id=active_conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        ) from exc

    await append_message(
        db_sessionmaker,
        conversation_id=active_conversation_id,
        role="user",
        content=prompt,
        has_image=True,
    )
    await log_study_interaction_values(
        db_sessionmaker,
        telegram_id=user.id,
        username=user.username,
        chat_id=user.id,
        question=f"{prompt} [mini_app_photo]",
        engine=Engine.GEMINI,
        subject_tag="mini_app_image",
    )

    try:
        client: GeminiClient = request.app.state.gemini_client
        answer = await client.answer_image(
            prompt,
            image_bytes,
            channel="web",
            history=history,
        )
    except AIBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini vision is busy. Please try again shortly.",
        ) from exc
    except Exception as exc:
        logger.exception("Mini App image question failed for telegram_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Shadow Mentor could not read that image.",
        ) from exc

    await append_message(
        db_sessionmaker,
        conversation_id=active_conversation_id,
        role="assistant",
        content=answer,
        engine=Engine.GEMINI,
    )
    return ChatResponse(
        answer=answer,
        engine="gemini",
        conversation_id=active_conversation_id,
    )
