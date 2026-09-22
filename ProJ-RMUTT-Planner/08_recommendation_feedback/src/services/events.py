from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.metrics import EVENTS_ACCEPTED, EVENTS_DUPLICATE, INGEST_LATENCY
from src.models import EventLog
from src.schemas.contracts import EventCreate, FeedbackCreate
from src.services.feedback import create_feedback
from src.services.privacy import scrub_payload


def _feedback_from_event(item: EventCreate) -> FeedbackCreate | None:
    if item.action != "feedback":
        return None
    payload = item.payload
    required = {"target_type", "target_id", "rating"}
    if not required.issubset(payload):
        return None
    return FeedbackCreate(
        source_feedback_id=str(payload.get("feedback_id")) if payload.get("feedback_id") else item.event_id,
        request_id=item.request_id,
        student_hash=item.student_hash,
        target_type=payload["target_type"],
        target_id=str(payload["target_id"]),
        rating=payload["rating"],
        reason=payload.get("reason"),
        preference_signal=payload.get("preference_signal", {}),
    )


def ingest_events(db: Session, items: list[EventCreate]) -> dict:
    accepted = 0
    duplicates = 0
    event_ids = {item.event_id for item in items if item.event_id}
    existing_ids = set()
    if event_ids:
        existing_ids = set(
            db.scalars(select(EventLog.event_id).where(EventLog.event_id.in_(event_ids))).all()
        )
    seen_ids: set[str] = set()
    feedback_items: list[FeedbackCreate] = []
    with INGEST_LATENCY.time():
        for item in items:
            if item.event_id and (item.event_id in existing_ids or item.event_id in seen_ids):
                duplicates += 1
                EVENTS_DUPLICATE.inc()
                continue
            values = dict(
                event_id=item.event_id,
                request_id=item.request_id,
                student_hash=item.student_hash,
                service=item.service,
                action=item.action,
                intent=item.intent,
                tools=item.tools,
                latency_ms=item.latency_ms,
                tokens_in=item.tokens_in,
                tokens_out=item.tokens_out,
                cost_est=item.cost_est,
                status=item.status,
                payload=scrub_payload(item.payload),
            )
            if item.occurred_at is not None:
                values["created_at"] = item.occurred_at
            event = EventLog(**values)
            try:
                with db.begin_nested():
                    db.add(event)
                    db.flush()
            except IntegrityError:
                duplicates += 1
                EVENTS_DUPLICATE.inc()
                continue
            if item.event_id:
                seen_ids.add(item.event_id)
            accepted += 1
            EVENTS_ACCEPTED.labels(service=item.service, action=item.action, status=item.status).inc()
            feedback = _feedback_from_event(item)
            if feedback:
                feedback_items.append(feedback)
        db.commit()
        for feedback in feedback_items:
            create_feedback(db, feedback)
    return {"accepted": accepted, "duplicates": duplicates, "received": len(items)}
