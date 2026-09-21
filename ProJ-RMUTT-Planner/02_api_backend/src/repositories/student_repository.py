from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Student, StudentPreference


async def get_by_username(db: AsyncSession, username: str) -> Student | None:
    result = await db.execute(select(Student).where(Student.username == username))
    return result.scalar_one_or_none()


async def get_by_student_id(db: AsyncSession, student_id: str) -> Student | None:
    result = await db.execute(select(Student).where(Student.student_id == student_id))
    return result.scalar_one_or_none()


async def get_preferences_by_student_id(db: AsyncSession, student_id: str) -> StudentPreference | None:
    result = await db.execute(
        select(StudentPreference).where(StudentPreference.student_id == student_id)
    )
    return result.scalar_one_or_none()
