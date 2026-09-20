from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _csv(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    log_level: str
    internal_api_token: str | None
    cors_origins: list[str]
    notify_channels: list[str]
    line_channel_token: str | None
    retention_days: int
    low_seat_threshold: int
    review_rating_threshold: int
    max_event_batch: int


@lru_cache
def get_settings() -> Settings:
    token = os.getenv("INTERNAL_API_TOKEN", "").strip() or None
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./feedback.db"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/3"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        internal_api_token=token,
        cors_origins=_csv("CORS_ORIGINS", "http://localhost:3000"),
        notify_channels=_csv("NOTIFY_CHANNELS", "web"),
        line_channel_token=os.getenv("LINE_CHANNEL_TOKEN") or None,
        retention_days=int(os.getenv("LOG_RETENTION_DAYS", "90")),
        low_seat_threshold=int(os.getenv("LOW_SEAT_THRESHOLD", "5")),
        review_rating_threshold=int(os.getenv("REVIEW_RATING_THRESHOLD", "2")),
        max_event_batch=int(os.getenv("MAX_EVENT_BATCH", "500")),
    )
