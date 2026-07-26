from __future__ import annotations

import unittest
from unittest.mock import patch

from bot.rate_limit import RateLimitExceeded, enforce_rate_limit


class FakePipeline:
    def __init__(self, counts: dict[str, int]) -> None:
        self.counts = counts
        self.key = ""

    async def __aenter__(self) -> FakePipeline:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def incr(self, key: str) -> FakePipeline:
        self.key = key
        return self

    def expire(self, _key: str, _seconds: int) -> FakePipeline:
        return self

    async def execute(self) -> tuple[int, bool]:
        self.counts[self.key] = self.counts.get(self.key, 0) + 1
        return self.counts[self.key], True


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def pipeline(self, *, transaction: bool) -> FakePipeline:
        self.transaction = transaction
        return FakePipeline(self.counts)


class RateLimitTests(unittest.IsolatedAsyncioTestCase):
    @patch("bot.rate_limit.time.time", return_value=121)
    async def test_allows_requests_within_limit(self, _time: object) -> None:
        redis = FakeRedis()

        await enforce_rate_limit(redis, namespace="telegram", user_id=7, limit=2)
        await enforce_rate_limit(redis, namespace="telegram", user_id=7, limit=2)

    @patch("bot.rate_limit.time.time", return_value=121)
    async def test_rejects_requests_over_limit_with_window_retry(self, _time: object) -> None:
        redis = FakeRedis()

        await enforce_rate_limit(redis, namespace="telegram", user_id=7, limit=1)
        with self.assertRaises(RateLimitExceeded) as context:
            await enforce_rate_limit(redis, namespace="telegram", user_id=7, limit=1)

        self.assertEqual(context.exception.retry_after, 59)


if __name__ == "__main__":
    unittest.main()
