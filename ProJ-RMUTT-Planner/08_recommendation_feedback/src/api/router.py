from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import require_internal_token
from src.core.config import get_settings
from src.core.database import check_db, get_db
from src.core.http import request_id_var, success
from src.models import Notification
from src.schemas.contracts import (
    AlertEvaluationRequest,
    EventBatchCreate,
    EventCreate,
    FeedbackCreate,
    RecommendationComposeRequest,
)
from src.services import alerts, analytics, data_privacy, events, recommendations
from src.services.calendar_export import CalendarSnapshot, export_snapshot
from src.services.feedback import create_feedback, feedback_to_dict

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True, "service": "08_recommendation_feedback", "version": "1.0.0"}


@router.get("/ready")
def ready():
    if not check_db():
        raise HTTPException(503, {"code": "DB_UNAVAILABLE", "message": "database is unavailable"})
    return {"ok": True, "database": "ready"}


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.post("/events", status_code=202)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    if not payload.request_id:
        payload = payload.model_copy(update={"request_id": request_id_var.get()})
    return success(events.ingest_events(db, [payload]), status_code=202)


@router.post("/events/batch", status_code=202)
def create_event_batch(payload: EventBatchCreate, db: Session = Depends(get_db)):
    if len(payload.events) > get_settings().max_event_batch:
        raise HTTPException(
            413,
            {
                "code": "BATCH_TOO_LARGE",
                "message": f"maximum {get_settings().max_event_batch} events per batch",
            },
        )
    request_id = request_id_var.get()
    items = [
        item if item.request_id else item.model_copy(update={"request_id": request_id})
        for item in payload.events
    ]
    return success(events.ingest_events(db, items), status_code=202)


@router.post("/feedback", status_code=201)
def submit_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)):
    if not payload.request_id:
        payload = payload.model_copy(update={"request_id": request_id_var.get()})
    item, duplicate = create_feedback(db, payload)
    return success(feedback_to_dict(item, duplicate), status_code=200 if duplicate else 201)


@router.post("/recommendations/compose")
def compose_recommendations(payload: RecommendationComposeRequest):
    return success(recommendations.compose(payload))


@router.post("/alerts/evaluate", dependencies=[Depends(require_internal_token)])
def evaluate_alerts(payload: AlertEvaluationRequest, db: Session = Depends(get_db)):
    created = alerts.evaluate(db, payload)
    return success({"created": len(created), "notifications": [alerts.serialize(item) for item in created]})


@router.get("/notifications/{student_hash}", dependencies=[Depends(require_internal_token)])
def list_notifications(
    student_hash: str,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = select(Notification).where(Notification.student_hash == student_hash)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    return success([alerts.serialize(item) for item in db.scalars(query)])


@router.get("/analytics/summary", dependencies=[Depends(require_internal_token)])
def analytics_summary(
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
):
    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=30)
    if start >= end:
        raise HTTPException(422, {"code": "INVALID_PERIOD", "message": "start must be before end"})
    return success(analytics.summary(db, start, end))


@router.get("/export/ics/{plan_id}")
def export_ics(plan_id: int):
    # Module 08 cannot verify ownership of module 02's plans. Fail closed.
    raise HTTPException(
        503,
        {"code": "PLAN_EXPORT_NOT_CONNECTED", "message": "ต้องส่งแผนที่ตรวจสิทธิ์แล้วผ่านโมดูล 02"},
    )


@router.post("/export/ics", dependencies=[Depends(require_internal_token)])
def export_ics_from_snapshot(payload: CalendarSnapshot):
    content = export_snapshot(payload)
    return Response(
        content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="plan-{payload.plan_id}.ics"'},
    )


@router.delete("/privacy/students/{student_hash}", dependencies=[Depends(require_internal_token)])
def delete_student_data(student_hash: str, db: Session = Depends(get_db)):
    return success({"deleted": data_privacy.delete_student_analytics(db, student_hash)})
