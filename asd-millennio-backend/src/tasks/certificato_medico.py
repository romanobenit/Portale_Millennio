"""
Task Celery per gli alert di scadenza del certificato medico (30/15/7 giorni
prima), sullo stesso pattern del silenzio-assenso tesseramento (Celery beat).

Per i minori l'email va al tutore (l'email del minore è sintetica, non reale).
"""
import asyncio
from datetime import date, timedelta

from celery.utils.log import get_task_logger
from sqlalchemy import select

from core.celery_app import celery_app
from core.database import WorkerSessionLocal
from models.socio import Socio
from models.tessera import Tessera
from modules.soci.email import invia_alert_certificato_medico

task_logger = get_task_logger(__name__)

GIORNI_ALERT = (30, 15, 7)


async def _invia_alert() -> int:
    inviati = 0
    async with WorkerSessionLocal() as db:
        for giorni in GIORNI_ALERT:
            target = date.today() + timedelta(days=giorni)
            rows = (await db.execute(
                select(Tessera, Socio)
                .join(Socio, Tessera.socio_id == Socio.id)
                .where(
                    Tessera.certificato_medico_scadenza == target,
                    Tessera.stato == "attiva",
                )
            )).all()

            for tessera, socio in rows:
                destinatario = socio
                nome_tesserato = None
                if socio.is_minor and socio.tutore_id:
                    tutore = (await db.execute(
                        select(Socio).where(Socio.id == socio.tutore_id)
                    )).scalar_one_or_none()
                    if tutore:
                        destinatario = tutore
                        nome_tesserato = f"{socio.nome} {socio.cognome}"

                if not destinatario.email:
                    continue

                ok = await invia_alert_certificato_medico(
                    to=destinatario.email,
                    nome=destinatario.nome,
                    giorni_mancanti=giorni,
                    scadenza=tessera.certificato_medico_scadenza.isoformat(),
                    numero_tessera=tessera.numero_tessera,
                    nome_tesserato=nome_tesserato,
                )
                if ok:
                    inviati += 1
    return inviati


@celery_app.task(name="tasks.certificato_medico.alert_scadenza_certificato")
def alert_scadenza_certificato() -> int:
    n = asyncio.run(_invia_alert())
    if n:
        task_logger.info("Alert scadenza certificato medico: %d email inviate.", n)
    return n
