from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import CurrentUser, current_user
from src.core.db import get_db
from src.core.envelope import success_envelope
from src.core.log_queue import get_log_queue
from src.schemas.envelope import SuccessEnvelope
from src.schemas.feedback import FeedbackRequest, FeedbackResponse
from src.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=SuccessEnvelope[FeedbackResponse])
async def submit_feedback(
    payload: FeedbackRequest,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    feedback = await feedback_service.submit_feedback(
        db,
        student_id=user.student_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        rating=payload.rating,
        reason=payload.reason,
    )
    # ส่งสำเนาไป 08 แบบไม่บล็อกผู้ใช้ผ่าน log_queue เดียวกับ validate/auto/chat (ไม่เรียก
    # adapter.send_feedback() ตรงๆ ตามที่ Prompt 9 ให้ feedback ไปทาง log_queue เหมือนกันหมด)
    get_log_queue().enqueue(
        {
            "event": "feedback",
            "id_hash": user.id_hash,
            "target_type": payload.target_type,
            "target_id": payload.target_id,
            "rating": payload.rating,
        }
    )
    data = FeedbackResponse(feedback_id=feedback.id)
    return success_envelope(data.model_dump())
