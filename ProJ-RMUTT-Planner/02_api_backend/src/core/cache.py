from __future__ import annotations

import hashlib
import json
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.core.logging import get_logger

logger = get_logger(__name__)


def make_cache_key(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


async def cache_get_json(redis_client: Redis, key: str) -> Any | None:
    """Redis ล่ม/timeout -> ข้าม cache (คืน None) + log warning ไม่ error"""
    try:
        raw = await redis_client.get(key)
    except RedisError:
        logger.warning("cache_get_failed", key=key)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def cache_set_json(redis_client: Redis, key: str, value: Any, ttl_seconds: int) -> None:
    """Redis ล่ม/timeout -> ข้าม cache เงียบๆ + log warning ไม่ error"""
    try:
        await redis_client.set(key, json.dumps(value, default=str, ensure_ascii=False), ex=ttl_seconds)
    except RedisError:
        logger.warning("cache_set_failed", key=key)
