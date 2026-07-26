from __future__ import annotations

import time

from fastapi import HTTPException, status
from redis.asyncio import Redis


async def enforce_rate_limit(redis_client: Redis, user_id: int, limit: int) -> None:
    minute = int(time.time() // 60)
    key = f"shadow-mentor:web-rate:{user_id}:{minute}"

    async with redis_client.pipeline(transaction=True) as pipeline:
        pipeline.incr(key)
        pipeline.expire(key, 90)
        count, _ = await pipeline.execute()

    if int(count) > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many questions at once. Please wait a moment.",
            headers={"Retry-After": "60"},
        )
