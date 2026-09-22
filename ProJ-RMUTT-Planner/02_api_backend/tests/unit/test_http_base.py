from __future__ import annotations

import httpx
import pytest

from src.adapters.http_base import HttpAdapterClient
from src.core.config import TimeoutPolicy
from src.core.errors import Upstream502Error


async def test_returns_response_on_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = HttpAdapterClient(
        base_url="http://module04",
        module="04",
        timeout_policy=TimeoutPolicy(seconds=1, retries=1),
        transport=httpx.MockTransport(handler),
    )
    response = await client.request("GET", "/courses")
    assert response.status_code == 200
    await client.aclose()


async def test_retries_on_5xx_then_succeeds() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 2:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    client = HttpAdapterClient(
        base_url="http://module04",
        module="04",
        timeout_policy=TimeoutPolicy(seconds=1, retries=1),
        transport=httpx.MockTransport(handler),
    )
    response = await client.request("GET", "/courses")
    assert response.status_code == 200
    assert attempts["count"] == 2
    await client.aclose()


async def test_raises_upstream_502_after_exhausting_retries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = HttpAdapterClient(
        base_url="http://module06",
        module="06",
        timeout_policy=TimeoutPolicy(seconds=1, retries=1),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(Upstream502Error) as exc_info:
        await client.request("POST", "/validate")
    assert exc_info.value.details == {"module": "06"}
    await client.aclose()


async def test_does_not_retry_on_4xx() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(404)

    client = HttpAdapterClient(
        base_url="http://module04",
        module="04",
        timeout_policy=TimeoutPolicy(seconds=1, retries=2),
        transport=httpx.MockTransport(handler),
    )
    response = await client.request("GET", "/courses/XXX/sections")
    assert response.status_code == 404
    assert attempts["count"] == 1
    await client.aclose()


async def test_timeout_raises_upstream_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = HttpAdapterClient(
        base_url="http://module05",
        module="05",
        timeout_policy=TimeoutPolicy(seconds=1, retries=0),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(Upstream502Error):
        await client.request("GET", "/students/1/context")
    await client.aclose()


async def test_forwards_request_id_header() -> None:
    from src.core.middleware import request_context

    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["x-request-id"] = request.headers.get("x-request-id", "")
        return httpx.Response(200, json={"ok": True})

    client = HttpAdapterClient(
        base_url="http://module04",
        module="04",
        timeout_policy=TimeoutPolicy(seconds=1, retries=0),
        transport=httpx.MockTransport(handler),
    )
    with request_context("req_forward_test"):
        await client.request("GET", "/courses")
    assert captured["x-request-id"] == "req_forward_test"
    await client.aclose()
