from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Feedback


async def create(
    db: AsyncSession,
    *,
    student_id: str,
    target_type: str,
    target_id: str,
    rating: int,
    reason: str | None,
) -> Feedback:
    feedback = Feedback(
        student_id=student_id,
        target_type=target_type,
        target_id=target_id,
        rating=rating,
        reason=reason,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback
