from __future__ import annotations

from typing import Any


class AppError(Exception):
    code: str = "INTERNAL_500"
    status_code: int = 500

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class Auth401Error(AppError):
    code = "AUTH_401"
    status_code = 401


class Forbidden403Error(AppError):
    code = "FORBIDDEN_403"
    status_code = 403


class NotFound404Error(AppError):
    code = "NOT_FOUND_404"
    status_code = 404


class Conflict409Error(AppError):
    code = "CONFLICT_409"
    status_code = 409


class Payload413Error(AppError):
    code = "PAYLOAD_413"
    status_code = 413


class Validation422Error(AppError):
    code = "VALIDATION_422"
    status_code = 422


class Rate429Error(AppError):
    code = "RATE_429"
    status_code = 429


class Upstream502Error(AppError):
    code = "UPSTREAM_502"
    status_code = 502


class NotImplemented501Error(AppError):
    code = "NOT_IMPLEMENTED_501"
    status_code = 501


class Internal500Error(AppError):
    code = "INTERNAL_500"
    status_code = 500
