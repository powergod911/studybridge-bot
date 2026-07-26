from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


async def enforce_rate_limit(
    redis_client: Redis,
    *,
    namespace: str,
    user_id: int,
    limit: int,
) -> None:
    now = int(time.time())
    minute = now // 60
    key = f"shadow-mentor:{namespace}-rate:{user_id}:{minute}"

    async with redis_client.pipeline(transaction=True) as pipeline:
        pipeline.incr(key)
        pipeline.expire(key, 90)
        count, _ = await pipeline.execute()

    if int(count) > limit:
        raise RateLimitExceeded(max(1, 60 - (now % 60)))
