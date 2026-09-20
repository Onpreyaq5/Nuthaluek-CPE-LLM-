from __future__ import annotations

import fakeredis
import httpx
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from src.core.redis import get_redis
from src.main import app

pytestmark = pytest.mark.db


class _BrokenRedis:
    async def incr(self, key: str):
        raise RedisConnectionError("down")

    async def expire(self, *args, **kwargs):
        raise RedisConnectionError("down")


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


async def test_login_rate_limit_returns_429_with_retry_after_after_5_per_minute() -> None:
    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        responses = [
            await client.post("/api/v1/auth/login", json={"username": "wrong", "password": "wrong"})
            for _ in range(6)
        ]

    assert [r.status_code for r in responses[:5]] == [401] * 5
    assert responses[5].status_code == 429
    assert responses[5].json()["error"]["code"] == "RATE_429"
    assert "Retry-After" in responses[5].headers


async def test_general_rate_limit_applies_per_student_after_60_per_minute(
    logged_in_client: httpx.AsyncClient,
) -> None:
    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    responses = [await logged_in_client.get("/api/v1/plans") for _ in range(61)]

    assert all(r.status_code == 200 for r in responses[:60])
    assert responses[60].status_code == 429
    assert responses[60].json()["error"]["code"] == "RATE_429"


async def test_rate_limit_fails_open_when_redis_down(logged_in_client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_redis] = lambda: _BrokenRedis()

    response = await logged_in_client.get("/api/v1/plans")

    assert response.status_code == 200  # Redis ล่ม -> fail open ไม่ error


async def test_rate_limit_does_not_apply_outside_api_v1_prefix() -> None:
    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        responses = [await client.get("/health") for _ in range(70)]

    assert all(r.status_code == 200 for r in responses)
