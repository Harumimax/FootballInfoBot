from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CronJobSpec:
    name: str
    hour: int
    minute: int


def registered_job_names() -> tuple[str, ...]:
    return (
        "daily_full_sync",
        "morning_push",
        "after_matchday_check",
        "cleanup",
    )


def mvp_push_job_specs() -> tuple[CronJobSpec, ...]:
    return (
        CronJobSpec(name="morning_push", hour=9, minute=0),
        CronJobSpec(name="after_matchday_check", hour=23, minute=0),
        CronJobSpec(name="after_matchday_check", hour=0, minute=0),
        CronJobSpec(name="after_matchday_check", hour=1, minute=0),
        CronJobSpec(name="after_matchday_check", hour=2, minute=0),
        CronJobSpec(name="after_matchday_check", hour=3, minute=0),
    )


def daily_full_sync_job_specs() -> tuple[CronJobSpec, ...]:
    return (
        CronJobSpec(name="daily_full_sync", hour=6, minute=0),
        CronJobSpec(name="daily_full_sync", hour=18, minute=0),
    )
