from __future__ import annotations

import time

from fastapi import Depends, Request
from jose import JWTError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.api.deps import SESSION_COOKIE_NAME
from src.core.errors import Rate429Error
from src.core.logging import get_logger
from src.core.redis import get_redis
from src.core.security import decode_access_token

logger = get_logger(__name__)

_WINDOW_SECONDS = 60
_GENERAL_LIMIT = 60  # ต่อ student_id (PLAN.md หัวข้อ 8 D6)
_CHAT_LIMIT = 10  # ต่อ student_id เฉพาะ /chat
_LOGIN_LIMIT = 5  # ต่อ IP เฉพาะ /auth/login

_RATE_LIMIT_MESSAGE = "เรียกถี่เกินกำหนด กรุณาลองใหม่ภายหลัง"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _identity(request: Request) -> str:
    """student_id จาก cookie session ถ้ามีและถอดรหัสได้ ไม่งั้น fallback เป็น IP

    ไม่ใช้ Depends(current_user) ตรงๆ เพราะ /auth/login ยังไม่มี session — ต้องปล่อยให้ไม่มี identity
    ที่ถอดได้ ไม่ใช่ 401 ทันที
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        try:
            payload = decode_access_token(token)
        except JWTError:
            payload = None
        if payload and payload.get("sub"):
            return f"student:{payload['sub']}"
    return f"ip:{_client_ip(request)}"


async def _check_and_increment(redis: Redis, *, scope: str, identity: str, limit: int) -> None:
    window = int(time.time() // _WINDOW_SECONDS)
    redis_key = f"ratelimit:{scope}:{identity}:{window}"

    try:
        count = await redis.incr(redis_key)
        if count == 1:
            await redis.expire(redis_key, _WINDOW_SECONDS)
    except RedisError:
        logger.warning("rate_limit_redis_down_fail_open", scope=scope)
        return

    if count > limit:
        retry_after = _WINDOW_SECONDS - int(time.time() % _WINDOW_SECONDS)
        raise Rate429Error(
            _RATE_LIMIT_MESSAGE, details={"scope": scope, "retry_after": retry_after}
        )


async def rate_limit(request: Request, redis: Redis = Depends(get_redis)) -> None:
    """Fixed-window rate limit ผ่าน Redis (dependency ระดับ api_router ทั้งก้อน)

    ทำเป็น FastAPI dependency แทน ASGI middleware เพื่อให้ใช้ Depends(get_redis) เดียวกับที่อื่นทั้งหมด
    (override ด้วย fakeredis ใน test ได้ตามปกติ — ถ้าทำเป็น middleware ตรงๆ จะเรียก get_redis() นอกระบบ
    dependency injection ทำให้ override ไม่ได้ และ test จริงจะพยายามต่อ Redis จริงจนค้าง)
    """
    path = request.url.path
    if path == "/api/v1/auth/login" and request.method == "POST":
        await _check_and_increment(
            redis, scope="login", identity=f"ip:{_client_ip(request)}", limit=_LOGIN_LIMIT
        )
    elif path == "/api/v1/chat" and request.method == "POST":
        await _check_and_increment(redis, scope="chat", identity=_identity(request), limit=_CHAT_LIMIT)
    else:
        await _check_and_increment(
            redis, scope="general", identity=_identity(request), limit=_GENERAL_LIMIT
        )
