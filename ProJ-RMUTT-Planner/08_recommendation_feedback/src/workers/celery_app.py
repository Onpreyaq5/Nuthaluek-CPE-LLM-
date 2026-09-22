from celery import Celery

from src.core.config import get_settings

settings = get_settings()
celery_app = Celery("rmutt_feedback", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    timezone="Asia/Bangkok",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
celery_app.autodiscover_tasks(["src.workers"])
