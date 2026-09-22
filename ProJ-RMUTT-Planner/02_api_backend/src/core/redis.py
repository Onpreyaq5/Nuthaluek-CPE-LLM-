from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from src.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().REDIS_URL, decode_responses=True)
