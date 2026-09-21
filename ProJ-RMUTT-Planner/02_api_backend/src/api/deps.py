from __future__ import annotations

from fastapi import Request
from jose import JWTError
from pydantic import BaseModel

from src.core.errors import Auth401Error, Forbidden403Error
from src.core.masking import hash_student_id
from src.core.security import decode_access_token

SESSION_COOKIE_NAME = "session"

_INVALID_SESSION_MESSAGE = "เซสชันไม่ถูกต้องหรือหมดอายุ กรุณาเข้าสู่ระบบใหม่"


class CurrentUser(BaseModel):
    student_id: str
    username: str
    role: str
    id_hash: str


async def current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise Auth401Error("กรุณาเข้าสู่ระบบ")

    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise Auth401Error(_INVALID_SESSION_MESSAGE) from exc

    student_id = payload.get("sub")
    username = payload.get("username")
    role = payload.get("role")
    if not student_id or not username or not role:
        raise Auth401Error(_INVALID_SESSION_MESSAGE)

    return CurrentUser(
        student_id=student_id, username=username, role=role, id_hash=hash_student_id(student_id)
    )


def ensure_owner(resource_student_id: str, user: CurrentUser) -> None:
    if resource_student_id != user.student_id:
        raise Forbidden403Error("ไม่มีสิทธิ์เข้าถึงข้อมูลนี้")
