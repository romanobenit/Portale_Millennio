from celery import Celery

from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "millennio",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.mint"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Rome",
    enable_utc=True,
    task_track_started=True,
    # Ack dopo il completamento del task — evita perdita in caso di crash worker
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Visibilità stato task per il retry
    task_store_eager_result=True,
)
