from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import EventLog, FeedbackEvent, ReviewItem


def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    values.sort()
    return values[max(0, int(len(values) * 0.95 + 0.9999) - 1)]


def summary(db: Session, start: datetime, end: datetime) -> dict:
    events = list(
        db.scalars(select(EventLog).where(EventLog.created_at >= start, EventLog.created_at <= end))
    )
    feedback = list(
        db.scalars(
            select(FeedbackEvent).where(
                FeedbackEvent.created_at >= start, FeedbackEvent.created_at <= end
            )
        )
    )
    pending_reviews = db.scalars(select(ReviewItem).where(ReviewItem.status == "pending")).all()
    action_counts = Counter(event.action for event in events)
    status_counts = Counter(event.status for event in events)
    service_counts = Counter(event.service for event in events)
    latencies = [event.latency_ms for event in events if event.latency_ms is not None]
    costs = sum(float(event.cost_est or 0) for event in events)
    token_in = sum(event.tokens_in or 0 for event in events)
    token_out = sum(event.tokens_out or 0 for event in events)
    plan_feedback = [item for item in feedback if item.target_type == "plan"]
    adopted = sum(1 for item in plan_feedback if item.rating >= 4)
    conflicts: Counter[str] = Counter()
    for event in events:
        if event.action in {"conflict", "plan.validate", "conflicts.check"}:
            for conflict in event.payload.get("conflicts", []):
                code = conflict.get("code") if isinstance(conflict, dict) else str(conflict)
                if code:
                    conflicts[code] += 1

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "events": {
            "total": len(events),
            "by_action": dict(action_counts.most_common()),
            "by_status": dict(status_counts.most_common()),
            "by_service": dict(service_counts.most_common()),
        },
        "performance": {
            "p95_latency_ms": _p95(latencies),
            "tokens_in": token_in,
            "tokens_out": token_out,
            "cost_est": round(costs, 6),
        },
        "feedback": {
            "total": len(feedback),
            "average_rating": round(sum(item.rating for item in feedback) / len(feedback), 2) if feedback else None,
            "negative_count": sum(1 for item in feedback if item.rating <= 2),
            "pending_review": len(pending_reviews),
            "plan_acceptance_rate": round(adopted / len(plan_feedback), 4) if plan_feedback else None,
        },
        "quality": {
            "unanswered_questions": action_counts.get("chat.unanswered", 0),
            "frequent_conflicts": dict(conflicts.most_common(10)),
        },
    }
