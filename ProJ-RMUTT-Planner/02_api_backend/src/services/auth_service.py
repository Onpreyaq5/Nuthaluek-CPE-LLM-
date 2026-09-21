from __future__ import annotations

import hmac

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.errors import Auth401Error
from src.core.security import create_access_token
from src.models import Student
from src.repositories import student_repository

_LOGIN_ERROR_MESSAGE = "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
_INVALID_SESSION_MESSAGE = "เซสชันไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่"


def _credentials_match(username: str, password: str, settings: Settings) -> bool:
    # เข้ารหัสเป็น bytes ก่อนเทียบเสมอ: hmac.compare_digest ไม่รองรับ str นอก ASCII
    username_ok = hmac.compare_digest(username.encode("utf-8"), settings.DEMO_USERNAME.encode("utf-8"))
    password_ok = hmac.compare_digest(password.encode("utf-8"), settings.DEMO_PASSWORD.encode("utf-8"))
    return username_ok and password_ok


async def login(
    db: AsyncSession, *, username: str, password: str, settings: Settings
) -> tuple[Student, str]:
    if not _credentials_match(username, password, settings):
        raise Auth401Error(_LOGIN_ERROR_MESSAGE)

    student = await student_repository.get_by_username(db, settings.DEMO_USERNAME)
    if student is None:
        # ยังไม่ได้ seed บัญชีเดโม (scripts/seed_demo.py) — ถือว่าล็อกอินไม่ได้เหมือนกัน ไม่บอกสาเหตุจริงให้ client
        raise Auth401Error(_LOGIN_ERROR_MESSAGE)

    token = create_access_token(student_id=student.student_id, username=student.username, role=student.role)
    return student, token


async def get_current_student(db: AsyncSession, student_id: str) -> Student:
    student = await student_repository.get_by_student_id(db, student_id)
    if student is None:
        raise Auth401Error(_INVALID_SESSION_MESSAGE)
    return student
