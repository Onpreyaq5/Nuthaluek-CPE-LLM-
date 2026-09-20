from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.core.errors import (
    AppError,
    Auth401Error,
    Conflict409Error,
    Forbidden403Error,
    Internal500Error,
    NotFound404Error,
    NotImplemented501Error,
    Payload413Error,
    Rate429Error,
    Upstream502Error,
    Validation422Error,
)
from src.core.middleware import RequestContextMiddleware
from src.main import app, app_error_handler, unhandled_error_handler, validation_error_handler

CASES = [
    (Auth401Error, "AUTH_401", 401),
    (Forbidden403Error, "FORBIDDEN_403", 403),
    (NotFound404Error, "NOT_FOUND_404", 404),
    (Conflict409Error, "CONFLICT_409", 409),
    (Payload413Error, "PAYLOAD_413", 413),
    (Validation422Error, "VALIDATION_422", 422),
    (Rate429Error, "RATE_429", 429),
    (Upstream502Error, "UPSTREAM_502", 502),
    (NotImplemented501Error, "NOT_IMPLEMENTED_501", 501),
    (Internal500Error, "INTERNAL_500", 500),
]


@pytest.mark.parametrize("error_cls,expected_code,expected_status", CASES)
def test_error_code_and_status(error_cls: type[AppError], expected_code: str, expected_status: int) -> None:
    error = error_cls("ข้อความทดสอบ", details={"key": "value"})
    assert error.code == expected_code
    assert error.status_code == expected_status
    assert error.message == "ข้อความทดสอบ"
    assert error.details == {"key": "value"}


class _RequiredFieldPayload(BaseModel):
    required_field: str


def _build_isolated_error_handling_app() -> FastAPI:
    """แอปแยกต่างหาก ใช้ exception handler + middleware ตัวจริงจาก src.main ทดสอบ
    error-handling pipeline โดยไม่พึ่ง business endpoint จริงของ app หลัก (ซึ่งตอนนี้ implement
    ครบทุกตัวแล้วตั้งแต่ Prompt 9 เลยไม่มี endpoint 501/ไม่ต้องล็อกอินให้ยืมทดสอบได้อีกต่อไป)
    """
    test_app = FastAPI()
    test_app.add_middleware(RequestContextMiddleware)
    test_app.add_exception_handler(AppError, app_error_handler)
    test_app.add_exception_handler(RequestValidationError, validation_error_handler)
    test_app.add_exception_handler(Exception, unhandled_error_handler)

    @test_app.post("/raise-not-implemented")
    async def _raise_not_implemented() -> None:
        raise NotImplemented501Error("ทดสอบ 501")

    @test_app.post("/raise-validation")
    async def _raise_validation(payload: _RequiredFieldPayload) -> dict:
        return {"ok": True}

    return test_app


def test_app_error_handler_returns_matching_status_and_request_id() -> None:
    with TestClient(_build_isolated_error_handling_app()) as client:
        response = client.post("/raise-not-implemented")

    assert response.status_code == 501
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "NOT_IMPLEMENTED_501"
    assert "X-Request-ID" in response.headers
    assert body["meta"]["request_id"] == response.headers["X-Request-ID"]


def test_validation_error_returns_422_with_details() -> None:
    with TestClient(_build_isolated_error_handling_app()) as client:
        response = client.post("/raise-validation", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "VALIDATION_422"
    assert "X-Request-ID" in response.headers


def test_health_returns_200() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
