from __future__ import annotations

import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(round((time.perf_counter() - started) * 1000, 2))
        return response


def success(data: object, *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"ok": True, "data": data, "meta": {"request_id": request_id_var.get()}},
    )


def _error(code: str, message: str, details: object | None, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "error": {"code": code, "message": message, "details": details},
            "meta": {"request_id": request_id_var.get()},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return _error(
            detail.get("code", f"HTTP_{exc.status_code}"),
            detail.get("message", "Request failed"),
            detail.get("details"),
            exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        details = [
            {key: value for key, value in item.items() if key not in {"ctx", "input"}}
            for item in exc.errors()
        ]
        return _error("VALIDATION_422", "ข้อมูลที่ส่งมาไม่ถูกต้อง", details, 422)
