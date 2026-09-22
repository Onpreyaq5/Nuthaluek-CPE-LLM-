from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import Forbidden403Error, NotFound404Error
from src.models import Feedback
from src.repositories import chat_repository, feedback_repository, plan_repository

_TARGET_NOT_FOUND_MESSAGE = "ไม่พบเป้าหมายที่จะให้ feedback"
_TARGET_FORBIDDEN_MESSAGE = "ไม่สามารถให้ feedback รายการของผู้อื่นได้"


def _not_found(target_type: str, target_id: str) -> NotFound404Error:
    return NotFound404Error(
        _TARGET_NOT_FOUND_MESSAGE, details={"target_type": target_type, "target_id": target_id}
    )


def _forbidden(target_type: str, target_id: str) -> Forbidden403Error:
    return Forbidden403Error(
        _TARGET_FORBIDDEN_MESSAGE, details={"target_type": target_type, "target_id": target_id}
    )


async def _ensure_target_owned(
    db: AsyncSession, *, target_type: str, target_id: str, student_id: str
) -> None:
    try:
        numeric_id = int(target_id)
    except ValueError as exc:
        raise _not_found(target_type, target_id) from exc

    # "explanation" ผูกกับแผน (ยังไม่มีที่เก็บ explanation แยกเป็นของตัวเอง) เช็ค ownership แบบเดียวกับ plan
    if target_type in ("plan", "explanation"):
        plan = await plan_repository.get_by_id(db, numeric_id)
        if plan is None:
            raise _not_found(target_type, target_id)
        if plan.student_id != student_id:
            raise _forbidden(target_type, target_id)
        return

    if target_type == "chat_message":
        message = await chat_repository.get_message_by_id(db, numeric_id)
        if message is None:
            raise _not_found(target_type, target_id)
        session = await chat_repository.get_session_by_id(db, message.session_id)
        if session is None or session.student_id != student_id:
            raise _forbidden(target_type, target_id)
        return

    raise _not_found(target_type, target_id)  # pragma: no cover - schema จำกัด target_type ไว้แล้ว


async def submit_feedback(
    db: AsyncSession,
    *,
    student_id: str,
    target_type: str,
    target_id: str,
    rating: int,
    reason: str | None,
) -> Feedback:
    await _ensure_target_owned(db, target_type=target_type, target_id=target_id, student_id=student_id)
    return await feedback_repository.create(
        db,
        student_id=student_id,
        target_type=target_type,
        target_id=target_id,
        rating=rating,
        reason=reason,
    )
