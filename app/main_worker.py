from __future__ import annotations

import asyncio
import logging

from app.config import load_settings
from app.scheduler.runner import run_worker


def main() -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level)
    if not settings.database_url:
        logging.getLogger(__name__).warning("DATABASE_URL is empty; worker is not started")
        return
    asyncio.run(run_worker(settings))


if __name__ == "__main__":
    main()
