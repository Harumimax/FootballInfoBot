from __future__ import annotations

import logging

from app.config import load_settings


def main() -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level)
    logging.getLogger(__name__).info("FootballInfoBot bot entrypoint is ready")


if __name__ == "__main__":
    main()
