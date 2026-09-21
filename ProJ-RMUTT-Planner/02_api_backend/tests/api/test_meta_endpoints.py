from __future__ import annotations

import httpx

from src.main import app


async def test_health_returns_ok_without_envelope() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_metrics_exposes_prometheus_text_including_log_dropped_total() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "log_dropped_total" in body
    assert "http_requests_total" in body or "http_request_duration" in body


async def test_metrics_and_health_are_not_under_api_v1_prefix() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await client.get("/api/v1/health")
        metrics = await client.get("/api/v1/metrics")

    assert health.status_code == 404
    assert metrics.status_code == 404
