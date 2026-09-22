from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Plan, PlanItem


async def get_by_student_term_name(
    db: AsyncSession, *, student_id: str, term: str, name: str
) -> Plan | None:
    result = await db.execute(
        select(Plan).where(Plan.student_id == student_id, Plan.term == term, Plan.name == name)
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, plan_id: int) -> Plan | None:
    # eager-load items เพราะ AsyncSession lazy-load แบบ implicit ไม่ได้ (MissingGreenlet)
    result = await db.execute(select(Plan).where(Plan.id == plan_id).options(selectinload(Plan.items)))
    return result.scalar_one_or_none()


async def list_by_student(
    db: AsyncSession, *, student_id: str, term: str | None, offset: int, limit: int
) -> tuple[list[Plan], int]:
    query = select(Plan).where(Plan.student_id == student_id).options(selectinload(Plan.items))
    if term:
        query = query.where(Plan.term == term)
    query = query.order_by(Plan.updated_at.desc(), Plan.id.desc())

    result = await db.execute(query)
    all_rows = list(result.scalars().all())  # จำนวนแผนต่อคนน้อยมาก ไม่คุ้มแยก COUNT query ต่างหาก
    return all_rows[offset : offset + limit], len(all_rows)


async def create_with_items(
    db: AsyncSession, *, student_id: str, term: str, name: str, section_ids: list[str]
) -> Plan:
    plan = Plan(student_id=student_id, term=term, name=name)
    plan.items = [PlanItem(section_id=sid, position=i) for i, sid in enumerate(section_ids)]
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def delete(db: AsyncSession, plan: Plan) -> None:
    await db.delete(plan)
    await db.commit()
