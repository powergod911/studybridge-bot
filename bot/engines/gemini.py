from __future__ import annotations

import asyncio
import logging
from io import BytesIO

from google import genai
from google.genai import errors, types
from PIL import Image

from bot.engines.errors import AIBusyError
from bot.router import GEMINI_MODEL

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def answer(self, prompt: str) -> str:
        return await self._with_retry(lambda: self._generate_text(prompt))

    async def answer_image(self, prompt: str, image_bytes: bytes) -> str:
        return await self._with_retry(lambda: self._generate_image(prompt, image_bytes))

    async def _with_retry(self, call) -> str:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return await asyncio.to_thread(call)
            except errors.APIError as exc:
                status = getattr(exc, "code", None)
                if status != 429:
                    raise
                last_error = exc
            except TimeoutError as exc:
                last_error = exc

            if attempt == 0:
                await asyncio.sleep(2)

        logger.warning("Gemini busy after retry: %s", last_error)
        raise AIBusyError("gemini busy") from last_error

    def _generate_text(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.5),
        )
        return response.text or "I could not generate an answer."

    def _generate_image(self, prompt: str, image_bytes: bytes) -> str:
        image = Image.open(BytesIO(image_bytes))
        response = self._client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image],
            config=types.GenerateContentConfig(temperature=0.5),
        )
        return response.text or "I could not generate an answer."
