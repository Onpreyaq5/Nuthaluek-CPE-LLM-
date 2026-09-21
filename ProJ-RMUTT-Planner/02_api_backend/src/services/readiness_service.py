from __future__ import annotations

import httpx
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import Settings

# ปลายทางสำหรับเช็ค readiness ของโมดูลอื่นเป็น PLACEHOLDER (สมมติว่ามี GET /health แบบเดียวกับ 02 เอง)
# ยังไม่มีสัญญาจริงจากทีมโมดูลไหนเลยว่า health-check endpoint จริงคืออะไร
_HTTP_HEALTH_PATH = "/health"
_HEALTH_CHECK_TIMEOUT_SECONDS = 3.0


async def check_database(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis(redis: Redis) -> bool:
    try:
        return bool(await redis.ping())
    except Exception:
        return False


async def check_http_module(
    base_url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> bool:
    try:
        async with httpx.AsyncClient(timeout=_HEALTH_CHECK_TIMEOUT_SECONDS, transport=transport) as client:
            response = await client.get(f"{base_url}{_HTTP_HEALTH_PATH}")
        return response.status_code < 500
    except Exception:
        return False


async def check_readiness(settings: Settings, engine: AsyncEngine, redis: Redis) -> dict[str, bool]:
    """Postgres, Redis เช็คเสมอ · โมดูล 04-08 เช็คเฉพาะตัวที่ตั้ง ADAPTER=http · 03 เช็คเสมอ (ใช้ http เสมอ)"""
    statuses: dict[str, bool] = {
        "postgres": await check_database(engine),
        "redis": await check_redis(redis),
    }

    module_urls = {
        "04": (settings.ADAPTER_04, settings.COURSE_CATALOG_URL),
        "05": (settings.ADAPTER_05, settings.STUDENT_DATA_URL),
        "06": (settings.ADAPTER_06, settings.PLAN_ENGINE_URL),
        "07": (settings.ADAPTER_07, settings.EXPLAINER_URL),
        "08": (settings.ADAPTER_08, settings.LOG_SINK_URL),
    }
    for module, (adapter_mode, url) in module_urls.items():
        if adapter_mode == "http":
            statuses[module] = await check_http_module(url)

    statuses["03"] = await check_http_module(settings.ROUTER_URL)

    return statuses
