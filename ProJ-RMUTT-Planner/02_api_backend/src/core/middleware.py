from __future__ import annotations

import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
_start_time_ctx: ContextVar[float] = ContextVar("start_time", default=0.0)


def get_request_id() -> str:
    return _request_id_ctx.get()


def get_took_ms() -> float:
    start = _start_time_ctx.get()
    if not start:
        return 0.0
    return round((time.perf_counter() - start) * 1000, 2)


def new_request_id() -> str:
    return f"req_{secrets.token_hex(8)}"


@contextmanager
def request_context(request_id: str) -> Iterator[None]:
    """ตั้งค่า request_id/start_time ชั่วคราว ใช้ใน unit test ที่ไม่ได้ผ่าน middleware จริง"""
    id_token = _request_id_ctx.set(request_id)
    time_token = _start_time_ctx.set(time.perf_counter())
    try:
        yield
    finally:
        _request_id_ctx.reset(id_token)
        _start_time_ctx.reset(time_token)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        id_token = _request_id_ctx.set(request_id)
        time_token = _start_time_ctx.set(time.perf_counter())
        try:
            response: Response = await call_next(request)
        finally:
            _request_id_ctx.reset(id_token)
            _start_time_ctx.reset(time_token)
        response.headers["X-Request-ID"] = request_id
        return response
