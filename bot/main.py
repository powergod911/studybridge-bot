from __future__ import annotations

import asyncio
import logging

from bot.config import load_settings
from bot.runtime import create_bot_application

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    try:
        settings = load_settings()
    except RuntimeError as exc:
        logger.critical("Startup validation failed: %s", exc)
        raise SystemExit(1) from exc

    application = create_bot_application(settings)
    try:
        await application.poll()
    finally:
        await application.close()


if __name__ == "__main__":
    asyncio.run(main())
