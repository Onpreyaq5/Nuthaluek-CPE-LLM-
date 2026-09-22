from __future__ import annotations

from typing import Any

from src.core.middleware import get_request_id, get_took_ms


def _meta() -> dict[str, Any]:
    return {"request_id": get_request_id(), "took_ms": get_took_ms()}


def success_envelope(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "meta": _meta()}


def error_envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code, "message": message, "details": details or {}},
        "meta": _meta(),
    }
