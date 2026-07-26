from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from bot.engines.errors import AIBusyError
from bot.prompts import ChatTurn, ResponseChannel, normalize_history, system_prompt
from bot.router import DEEPSEEK_MODEL

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class DeepSeekClient:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=60,
        )

    async def answer(
        self,
        prompt: str,
        *,
        channel: ResponseChannel = "telegram",
        history: Sequence[ChatTurn] | None = None,
    ) -> str:
        last_error: Exception | None = None
        messages = [
            {"role": "system", "content": system_prompt(channel)},
            *normalize_history(history),
            {"role": "user", "content": prompt},
        ]

        for attempt in range(3):
            try:
                response = await self._client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=messages,
                    temperature=0.2,
                )
                return response.choices[0].message.content or "I could not generate an answer."
            except (APITimeoutError, APIConnectionError) as exc:
                last_error = exc
            except APIStatusError as exc:
                if exc.status_code not in RETRYABLE_STATUS_CODES:
                    raise
                last_error = exc

            if attempt < 2:
                await asyncio.sleep(2**attempt)

        logger.warning("DeepSeek busy after retry: %s", last_error)
        raise AIBusyError("deepseek busy") from last_error
