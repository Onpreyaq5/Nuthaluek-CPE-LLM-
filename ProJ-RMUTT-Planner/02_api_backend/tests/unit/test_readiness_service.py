from __future__ import annotations

import httpx

from src.core.config import get_settings
from src.services.readiness_service import (
    check_database,
    check_http_module,
    check_readiness,
    check_redis,
)


class _FakeConnection:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def execute(self, _statement):
        if self._fail:
            raise RuntimeError("db down")
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    def connect(self):
        return _FakeConnection(fail=self._fail)


class _FakeRedis:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def ping(self) -> bool:
        if self._fail:
            raise RuntimeError("redis down")
        return True


async def test_check_database_true_when_query_succeeds() -> None:
    assert await check_database(_FakeEngine()) is True


async def test_check_database_false_when_connection_fails() -> None:
    assert await check_database(_FakeEngine(fail=True)) is False


async def test_check_redis_true_when_ping_succeeds() -> None:
    assert await check_redis(_FakeRedis()) is True


async def test_check_redis_false_when_ping_fails() -> None:
    assert await check_redis(_FakeRedis(fail=True)) is False


async def test_check_http_module_true_for_2xx_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})

    result = await check_http_module("http://module", transport=httpx.MockTransport(handler))

    assert result is True


async def test_check_http_module_false_for_5xx_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    result = await check_http_module("http://module", transport=httpx.MockTransport(handler))

    assert result is False


async def test_check_http_module_false_when_transport_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    result = await check_http_module("http://module", transport=httpx.MockTransport(handler))

    assert result is False


async def test_check_readiness_only_checks_http_modules_when_adapter_is_http(monkeypatch) -> None:
    checked_urls: list[str] = []

    async def fake_check_http_module(base_url: str, *, transport=None) -> bool:
        checked_urls.append(base_url)
        return True

    monkeypatch.setattr(
        "src.services.readiness_service.check_http_module", fake_check_http_module
    )

    settings = get_settings().model_copy(
        update={
            "ADAPTER_04": "http",
            "ADAPTER_05": "mock",
            "ADAPTER_06": "inprocess",
            "ADAPTER_07": "mock",
            "ADAPTER_08": "http",
        }
    )

    result = await check_readiness(settings, _FakeEngine(), _FakeRedis())

    assert result["postgres"] is True
    assert result["redis"] is True
    assert result["04"] is True
    assert result["08"] is True
    assert "05" not in result
    assert "06" not in result
    assert "07" not in result
    assert result["03"] is True
    assert settings.COURSE_CATALOG_URL in checked_urls
    assert settings.LOG_SINK_URL in checked_urls
    assert settings.ROUTER_URL in checked_urls


async def test_check_readiness_reflects_database_and_redis_failures() -> None:
    settings = get_settings().model_copy(
        update={
            "ADAPTER_04": "mock",
            "ADAPTER_05": "mock",
            "ADAPTER_06": "mock",
            "ADAPTER_07": "mock",
            "ADAPTER_08": "mock",
        }
    )

    result = await check_readiness(settings, _FakeEngine(fail=True), _FakeRedis(fail=True))

    assert result["postgres"] is False
    assert result["redis"] is False
