"""สร้าง/อัปเดตบัญชีเดโม (DEMO_STUDENT_ID/DEMO_USERNAME) แบบ idempotent — รันซ้ำได้ไม่พัง

ใช้: python -m scripts.seed_demo   (หรือรันเป็นส่วนหนึ่งของ entrypoint.sh ใน Prompt 5)
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.core.asyncio_compat import ensure_selector_event_loop_policy_on_windows
from src.core.config import get_settings
from src.core.db import get_sessionmaker
from src.models import Plan, PlanItem, Student, StudentPreference

ensure_selector_event_loop_policy_on_windows()

_SAMPLE_PLAN_TERM = "1/2569"
_SAMPLE_PLAN_NAME = "แผนหลัก"
_SAMPLE_PLAN_SECTION_IDS = ["CPE301-02", "GE101-01"]  # ไม่ชนกัน ยืนยันแล้วใน tests/unit/test_mock_plan_engine.py


async def seed_demo() -> None:
    settings = get_settings()
    session_factory = get_sessionmaker()

    async with session_factory() as session:
        result = await session.execute(
            select(Student).where(Student.student_id == settings.DEMO_STUDENT_ID)
        )
        student = result.scalar_one_or_none()
        if student is None:
            student = Student(
                student_id=settings.DEMO_STUDENT_ID, username=settings.DEMO_USERNAME, role="student"
            )
            session.add(student)
        else:
            student.username = settings.DEMO_USERNAME
            student.role = "student"

        result = await session.execute(
            select(StudentPreference).where(StudentPreference.student_id == settings.DEMO_STUDENT_ID)
        )
        preference = result.scalar_one_or_none()
        if preference is None:
            session.add(
                StudentPreference(
                    student_id=settings.DEMO_STUDENT_ID,
                    free_days=["FRI"],
                    no_early_class=False,
                    max_credits=21,
                )
            )

        result = await session.execute(
            select(Plan).where(
                Plan.student_id == settings.DEMO_STUDENT_ID,
                Plan.term == _SAMPLE_PLAN_TERM,
                Plan.name == _SAMPLE_PLAN_NAME,
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            plan = Plan(
                student_id=settings.DEMO_STUDENT_ID, term=_SAMPLE_PLAN_TERM, name=_SAMPLE_PLAN_NAME
            )
            plan.items = [
                PlanItem(section_id=section_id, position=i)
                for i, section_id in enumerate(_SAMPLE_PLAN_SECTION_IDS)
            ]
            session.add(plan)

        await session.commit()

    print(f"seed_demo: ok (student_id={settings.DEMO_STUDENT_ID}, username={settings.DEMO_USERNAME})")


if __name__ == "__main__":
    asyncio.run(seed_demo())
