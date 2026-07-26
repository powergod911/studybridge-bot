from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from io import BytesIO

from google import genai
from google.genai import errors, types
from PIL import Image

from bot.engines.errors import AIBusyError
from bot.prompts import ChatTurn, ResponseChannel, prompt_with_history, system_prompt
from bot.router import GEMINI_MODEL

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiClient:
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def answer(
        self,
        prompt: str,
        *,
        channel: ResponseChannel = "telegram",
        history: Sequence[ChatTurn] | None = None,
    ) -> str:
        return await self._with_retry(
            lambda: self._generate_text(prompt, channel=channel, history=history)
        )

    async def answer_image(
        self,
        prompt: str,
        image_bytes: bytes,
        *,
        channel: ResponseChannel = "telegram",
    ) -> str:
        return await self._with_retry(
            lambda: self._generate_image(prompt, image_bytes, channel=channel)
        )

    async def _with_retry(self, call: Callable[[], str]) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await asyncio.to_thread(call)
            except errors.APIError as exc:
                status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                if status not in RETRYABLE_STATUS_CODES:
                    raise
                last_error = exc
            except TimeoutError as exc:
                last_error = exc

            if attempt < 2:
                await asyncio.sleep(2**attempt)

        logger.warning("Gemini busy after retry: %s", last_error)
        raise AIBusyError("gemini busy") from last_error

    def _generate_text(
        self,
        prompt: str,
        *,
        channel: ResponseChannel,
        history: Sequence[ChatTurn] | None,
    ) -> str:
        response = self._client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt_with_history(prompt, history),
            config=types.GenerateContentConfig(
                system_instruction=system_prompt(channel),
                temperature=0.35,
            ),
        )
        return response.text or "I could not generate an answer."

    def _generate_image(
        self,
        prompt: str,
        image_bytes: bytes,
        *,
        channel: ResponseChannel,
    ) -> str:
        with Image.open(BytesIO(image_bytes)) as source:
            image = source.convert("RGB").copy()
        response = self._client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt(channel),
                temperature=0.35,
            ),
        )
        return response.text or "I could not generate an answer."
