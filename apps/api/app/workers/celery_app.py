"""Celery application instance and configuration."""

from celery import Celery

from app.core.config import settings

# In test mode or when eager execution is enabled, use in-memory broker to avoid socket timeouts
is_test_or_eager = settings.CELERY_TASK_ALWAYS_EAGER or settings.APP_ENV == "test"
broker_url = "memory://" if is_test_or_eager else settings.REDIS_URL
backend_url = "cache+memory://" if is_test_or_eager else settings.REDIS_URL

celery_app = Celery(
    "codeguard_worker",
    broker=broker_url,
    backend=backend_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_always_eager=is_test_or_eager,
    broker_connection_retry_on_startup=not is_test_or_eager,
)
