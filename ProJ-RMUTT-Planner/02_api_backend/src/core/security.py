from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt

from src.core.config import get_settings

_ALGORITHM = "HS256"


def create_access_token(*, student_id: str, username: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": student_id,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """คืน payload ถ้า token ถูกต้องและยังไม่หมดอายุ · raise jose.JWTError ทุกกรณีอื่น
    (หมดอายุ/ปลอม/รูปแบบผิด) ให้ผู้เรียก (dependency current_user) แปลงเป็น AUTH_401 เอง
    """
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
