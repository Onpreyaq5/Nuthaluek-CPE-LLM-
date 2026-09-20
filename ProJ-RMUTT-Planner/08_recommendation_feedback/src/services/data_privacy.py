from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.models import EventLog, FeedbackEvent, Notification


def delete_student_analytics(db: Session, student_hash: str) -> dict:
    counts = {}
    for name, model in (
        ("events", EventLog),
        ("feedback", FeedbackEvent),
        ("notifications", Notification),
    ):
        result = db.execute(delete(model).where(model.student_hash == student_hash))
        counts[name] = result.rowcount or 0
    db.commit()
    return counts
