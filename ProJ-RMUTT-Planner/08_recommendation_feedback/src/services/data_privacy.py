from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models import EventLog, FeedbackEvent, Notification, ReviewItem


def delete_student_analytics(db: Session, student_hash: str) -> dict:
    counts = {}
    feedback_ids = select(FeedbackEvent.id).where(FeedbackEvent.student_hash == student_hash)
    reviews = db.execute(delete(ReviewItem).where(ReviewItem.feedback_event_id.in_(feedback_ids)))
    counts["reviews"] = reviews.rowcount or 0
    for name, model in (
        ("events", EventLog),
        ("feedback", FeedbackEvent),
        ("notifications", Notification),
    ):
        result = db.execute(delete(model).where(model.student_hash == student_hash))
        counts[name] = result.rowcount or 0
    db.commit()
    return counts
