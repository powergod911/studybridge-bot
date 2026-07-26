from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from web.telegram_auth import TelegramUser, validate_init_data


async def require_telegram_user(
    request: Request,
    init_data: Annotated[
        str | None,
        Header(alias="X-Telegram-Init-Data"),
    ] = None,
) -> TelegramUser:
    settings = request.app.state.settings
    if settings.dev_mode and not init_data:
        return TelegramUser(id=0, first_name="Preview Student", username="preview")

    try:
        return validate_init_data(
            init_data or "",
            settings.telegram_bot_token,
            max_age_seconds=settings.telegram_auth_max_age_seconds,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Open Shadow Mentor from Telegram to continue.",
        ) from exc
