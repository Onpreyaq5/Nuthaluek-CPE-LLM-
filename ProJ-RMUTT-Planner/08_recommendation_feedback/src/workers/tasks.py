from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from src.core.config import get_settings
from src.core.database import SessionLocal
from src.models import EventLog
from src.workers.celery_app import celery_app


@celery_app.task(name="feedback.purge_expired_event_logs")
def purge_expired_event_logs() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=get_settings().retention_days)
    with SessionLocal() as db:
        result = db.execute(delete(EventLog).where(EventLog.created_at < cutoff))
        db.commit()
        return result.rowcount or 0
