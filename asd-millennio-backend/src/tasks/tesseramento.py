"""
Task Celery per l'auto-conferma dei tesseramenti (silenzio-assenso a 30 giorni).

Ogni giorno: i tesseramenti attivi provvisori la cui finestra di verifica è
scaduta senza azione dello staff vengono confermati automaticamente.
"""
import asyncio

from celery.utils.log import get_task_logger

from core.celery_app import celery_app
from core.database import WorkerSessionLocal
from modules.soci.tesseramento_service import TesseramentoService

task_logger = get_task_logger(__name__)


async def _auto_conferma() -> int:
    async with WorkerSessionLocal() as db:
        n = await TesseramentoService(db).auto_conferma_scadute()
        await db.commit()
        return n


@celery_app.task(name="tasks.tesseramento.auto_conferma_tesseramenti")
def auto_conferma_tesseramenti() -> int:
    n = asyncio.run(_auto_conferma())
    if n:
        task_logger.info("Auto-conferma tesseramenti: %d confermati (silenzio-assenso).", n)
    return n
