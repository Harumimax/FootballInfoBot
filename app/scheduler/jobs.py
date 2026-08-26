from __future__ import annotations


def registered_job_names() -> tuple[str, ...]:
    return (
        "daily_full_sync",
        "morning_push",
        "after_matchday_check",
        "cleanup",
    )
