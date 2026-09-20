from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.metrics import FEEDBACK_ACCEPTED
from src.models import FeedbackEvent, ReviewItem
from src.schemas.contracts import FeedbackCreate
from src.services.privacy import scrub_payload, scrub_text


def create_feedback(db: Session, item: FeedbackCreate) -> tuple[FeedbackEvent, bool]:
    if item.source_feedback_id:
        existing = db.scalar(
            select(FeedbackEvent).where(FeedbackEvent.source_feedback_id == item.source_feedback_id)
        )
        if existing:
            return existing, True

    feedback = FeedbackEvent(
        source_feedback_id=item.source_feedback_id,
        request_id=item.request_id,
        student_hash=item.student_hash,
        target_type=item.target_type,
        target_id=item.target_id,
        rating=item.rating,
        reason=scrub_text(item.reason) if item.reason else None,
        preference_signal=scrub_payload(item.preference_signal),
    )
    db.add(feedback)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(FeedbackEvent).where(FeedbackEvent.source_feedback_id == item.source_feedback_id)
        )
        if existing:
            return existing, True
        raise

    if item.rating <= get_settings().review_rating_threshold:
        category = "retrieval" if item.target_type == "chat_message" else "quality"
        db.add(ReviewItem(feedback_event_id=feedback.id, category=category))
    db.commit()
    db.refresh(feedback)
    FEEDBACK_ACCEPTED.labels(target_type=item.target_type, rating=str(item.rating)).inc()
    return feedback, False


def feedback_to_dict(item: FeedbackEvent, duplicate: bool = False) -> dict:
    return {
        "feedback_id": item.id,
        "duplicate": duplicate,
        "review_queued": item.rating <= get_settings().review_rating_threshold,
    }
