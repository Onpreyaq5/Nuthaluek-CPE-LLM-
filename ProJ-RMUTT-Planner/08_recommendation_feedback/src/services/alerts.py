from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.metrics import ALERTS_CREATED
from src.models import Notification
from src.schemas.contracts import AlertEvaluationRequest


def _save(
    db: Session,
    *,
    student_hash: str,
    code: str,
    title: str,
    message: str,
    reference_id: str,
    as_of: str,
) -> Notification | None:
    dedup_key = f"{student_hash}:{code}:{reference_id}:{as_of}"
    existing = db.scalar(select(Notification).where(Notification.dedup_key == dedup_key))
    if existing:
        return None
    item = Notification(
        student_hash=student_hash,
        code=code,
        title=title,
        message=message,
        reference_id=reference_id,
        channel="web",
        dedup_key=dedup_key,
        status="sent",
    )
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        return None
    ALERTS_CREATED.labels(code=code, channel="web").inc()
    return item


def evaluate(db: Session, request: AlertEvaluationRequest) -> list[Notification]:
    created: list[Notification] = []
    as_of = request.as_of.isoformat()
    for event in request.academic_events:
        days = (event.event_date - request.as_of).days
        if event.event_type == "registration" and days in {7, 3, 1}:
            item = _save(
                db,
                student_hash=request.student_hash,
                code="A1",
                title="ใกล้วันลงทะเบียน",
                message=f"เหลืออีก {days} วันถึงวันลงทะเบียน ({event.event_date.isoformat()})",
                reference_id=f"registration:{event.event_date}",
                as_of=as_of,
            )
            if item:
                created.append(item)
        if event.event_type == "withdraw" and 0 <= days <= 7:
            item = _save(
                db,
                student_hash=request.student_hash,
                code="A4",
                title="ใกล้วันสุดท้ายของการถอนรายวิชา",
                message=f"เหลืออีก {days} วันถึงกำหนดถอน ({event.event_date.isoformat()})",
                reference_id=f"withdraw:{event.event_date}",
                as_of=as_of,
            )
            if item:
                created.append(item)

    threshold = get_settings().low_seat_threshold
    for section in request.planned_sections:
        if section.seats_remaining is not None and section.seats_remaining < threshold:
            item = _save(
                db,
                student_hash=request.student_hash,
                code="A2",
                title="ที่นั่งใกล้เต็ม",
                message=f"{section.course_code} เหลือ {section.seats_remaining} ที่นั่ง",
                reference_id=section.section_id,
                as_of=as_of,
            )
            if item:
                created.append(item)
        if section.cancelled or section.schedule_changed:
            change = "ถูกยกเลิก" if section.cancelled else "เปลี่ยนเวลา"
            item = _save(
                db,
                student_hash=request.student_hash,
                code="A3",
                title="แผนการเรียนต้องตรวจสอบใหม่",
                message=f"{section.course_code} {change} กรุณาจัดแผนใหม่",
                reference_id=section.section_id,
                as_of=as_of,
            )
            if item:
                created.append(item)

    if request.planned_credits is not None and request.planned_credits < request.min_credits:
        item = _save(
            db,
            student_hash=request.student_hash,
            code="A5",
            title="หน่วยกิตต่ำกว่าเกณฑ์",
            message=f"แผนมี {request.planned_credits} หน่วยกิต ต่ำกว่าเกณฑ์ {request.min_credits}",
            reference_id="credits",
            as_of=as_of,
        )
        if item:
            created.append(item)
    return created


def serialize(item: Notification) -> dict:
    return {
        "id": item.id,
        "code": item.code,
        "title": item.title,
        "message": item.message,
        "reference_id": item.reference_id,
        "channel": item.channel,
        "status": item.status,
        "is_read": item.is_read,
        "created_at": item.created_at.isoformat(),
    }
