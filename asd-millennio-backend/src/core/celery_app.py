from celery import Celery
from celery.schedules import crontab

from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "millennio",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.mint", "tasks.tesseramento"],
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
    # Le transazioni on-chain (mint) vanno su una coda dedicata servita da un
    # worker a concorrenza 1: serializza i mint ed evita la collisione di nonce.
    task_routes={
        "tasks.mint.esegui_mint_task": {"queue": "mint"},
    },
    task_default_queue="celery",
    # Silenzio-assenso: auto-conferma giornaliera dei tesseramenti scaduti (03:00).
    beat_schedule={
        "auto-conferma-tesseramenti": {
            "task": "tasks.tesseramento.auto_conferma_tesseramenti",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)
