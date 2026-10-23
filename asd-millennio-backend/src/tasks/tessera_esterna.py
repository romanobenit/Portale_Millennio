"""
Alert di scadenza della tessera di un'altra ASD (iscrizione community), 30/15/7
giorni prima, sullo stesso pattern del certificato medico. Si avvisa solo per la
tessera più recente: se è già stata caricata quella rinnovata, nessun avviso.
Per i minori l'email va al tutore.
"""
import asyncio
from datetime import date, timedelta

from celery.utils.log import get_task_logger
from sqlalchemy import and_, exists, select
from sqlalchemy.orm import aliased

from core.celery_app import celery_app
from core.database import WorkerSessionLocal
from models.socio import Socio
from models.tessera import Tessera
from models.tessera_esterna import TesseraEsterna
from modules.soci.email import invia_alert_tessera_esterna

task_logger = get_task_logger(__name__)

GIORNI_ALERT = (30, 15, 7)


async def _invia_alert() -> int:
    inviati = 0
    Nuova = aliased(TesseraEsterna)
    async with WorkerSessionLocal() as db:
        for giorni in GIORNI_ALERT:
            target = date.today() + timedelta(days=giorni)
            rows = (await db.execute(
                select(TesseraEsterna, Socio)
                .join(Socio, TesseraEsterna.socio_id == Socio.id)
                .where(
                    TesseraEsterna.data_scadenza == target,
                    TesseraEsterna.verifica_stato != "rifiutata",
                    exists().where(and_(
                        Tessera.socio_id == TesseraEsterna.socio_id,
                        Tessera.sport == "community",
                        Tessera.stato == "attiva",
                    )),
                    ~exists().where(and_(
                        Nuova.socio_id == TesseraEsterna.socio_id,
                        Nuova.data_scadenza > target,
                        Nuova.verifica_stato != "rifiutata",
                    )),
                )
            )).all()

            for te, socio in rows:
                destinatario, nome_tesserato = socio, None
                if socio.is_minor and socio.tutore_id:
                    tutore = (await db.execute(select(Socio).where(Socio.id == socio.tutore_id))).scalar_one_or_none()
                    if tutore:
                        destinatario, nome_tesserato = tutore, f"{socio.nome} {socio.cognome}"
                if not destinatario.email:
                    continue
                if await invia_alert_tessera_esterna(
                    to=destinatario.email,
                    nome=destinatario.nome,
                    giorni_mancanti=giorni,
                    scadenza=te.data_scadenza.strftime("%d/%m/%Y"),
                    asd_nome=te.asd_nome,
                    nome_tesserato=nome_tesserato,
                ):
                    inviati += 1
    return inviati


@celery_app.task(name="tasks.tessera_esterna.alert_scadenza_tessera_esterna")
def alert_scadenza_tessera_esterna() -> int:
    n = asyncio.run(_invia_alert())
    if n:
        task_logger.info("Alert scadenza tessera esterna: %d email inviate.", n)
    return n
