from fastapi import Header, HTTPException

from src.core.config import get_settings


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    expected = get_settings().internal_api_token
    if expected and x_internal_token != expected:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_401", "message": "invalid internal service token"},
        )
