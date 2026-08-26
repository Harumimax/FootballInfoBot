from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Europe/Moscow"
DEFAULT_KULICHKI_BASE_URL = "https://football.kulichki.net"


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    database_url: str
    admin_user_ids: frozenset[int]
    app_env: str
    log_level: str
    timezone: str
    kulichki_base_url: str
    kulichki_user_agent: str

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def load_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", ""),
        admin_user_ids=parse_admin_user_ids(os.getenv("ADMIN_USER_IDS", "")),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        timezone=os.getenv("TIMEZONE", DEFAULT_TIMEZONE),
        kulichki_base_url=os.getenv("KULICHKI_BASE_URL", DEFAULT_KULICHKI_BASE_URL).rstrip("/"),
        kulichki_user_agent=os.getenv(
            "KULICHKI_USER_AGENT",
            "FootballInfoBot/0.1 (+https://github.com/Harumimax/FootballInfoBot)",
        ),
    )


def parse_admin_user_ids(raw_value: str) -> frozenset[int]:
    user_ids: set[int] = set()

    for chunk in raw_value.split(","):
        value = chunk.strip()
        if not value:
            continue
        user_ids.add(int(value))

    return frozenset(user_ids)
