from __future__ import annotations

from fastapi import HTTPException, status
from redis.asyncio import Redis

from bot.rate_limit import RateLimitExceeded
from bot.rate_limit import enforce_rate_limit as enforce_shared_rate_limit


async def enforce_rate_limit(redis_client: Redis, user_id: int, limit: int) -> None:
    try:
        await enforce_shared_rate_limit(
            redis_client,
            namespace="web",
            user_id=user_id,
            limit=limit,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many questions at once. Please wait a moment.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
