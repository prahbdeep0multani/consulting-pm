from celery import Celery
from celery.schedules import crontab

from ..config import settings

celery_app = Celery(
    "billing",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.invoice_tasks"],
)

celery_app.conf.beat_schedule = {
    "check-overdue-invoices": {
        "task": "app.tasks.invoice_tasks.check_overdue_invoices",
        "schedule": crontab(hour=8, minute=0),  # Daily at 08:00 UTC
    },
}
celery_app.conf.timezone = "UTC"
