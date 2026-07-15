from __future__ import annotations

import asyncio
import logging

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from bot.engines.errors import AIBusyError
from bot.router import DEEPSEEK_MODEL

logger = logging.getLogger(__name__)


class DeepSeekClient:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=60,
        )

    async def answer(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = await self._client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are StudyBridge, a concise A/L study helper. Show steps when solving.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )
                return response.choices[0].message.content or "I could not generate an answer."
            except (APITimeoutError, APIConnectionError) as exc:
                last_error = exc
            except APIStatusError as exc:
                if exc.status_code != 429:
                    raise
                last_error = exc

            if attempt == 0:
                await asyncio.sleep(2)

        logger.warning("DeepSeek busy after retry: %s", last_error)
        raise AIBusyError("deepseek busy") from last_error
