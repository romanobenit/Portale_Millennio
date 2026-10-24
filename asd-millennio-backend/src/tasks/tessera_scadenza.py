"""
Alert di scadenza delle tessere Millennio (30/15/7 giorni prima del 30 giugno),
sullo stesso pattern di certificato medico e tessera esterna. Un'email per
destinatario con tutte le sue tessere in scadenza (il tutore riceve anche quelle
dei figli minori). Non si avvisa per una categoria già rinnovata nell'anno
sportivo successivo. L'iscrizione community non scade e resta esclusa.
"""
import asyncio
from collections import defaultdict
from datetime import date, timedelta

from celery.utils.log import get_task_logger
from sqlalchemy import select

from core.celery_app import celery_app
from core.database import WorkerSessionLocal
from models.socio import Socio
from models.tessera import Tessera
from modules.soci.email import invia_alert_scadenza_tessera
from modules.soci.pdf import SPORT_LABEL

task_logger = get_task_logger(__name__)

GIORNI_ALERT = (30, 15, 7)


def gia_rinnovata(tessera, altre) -> bool:
    """True se tra `altre` (tessere attive o in pagamento dello stesso socio) c'è un rinnovo della stessa categoria."""
    return any(
        a.sport == tessera.sport
        and a.id != tessera.id
        and a.data_scadenza is not None
        and a.data_scadenza > tessera.data_scadenza
        for a in altre
    )


async def _invia_alert() -> int:
    inviati = 0
    async with WorkerSessionLocal() as db:
        for giorni in GIORNI_ALERT:
            target = date.today() + timedelta(days=giorni)
            in_scadenza = (await db.execute(
                select(Tessera, Socio)
                .join(Socio, Tessera.socio_id == Socio.id)
                .where(
                    Tessera.data_scadenza == target,
                    Tessera.stato == "attiva",
                    Tessera.sport != "community",
                )
            )).all()
            if not in_scadenza:
                continue

            socio_ids = {s.id for _, s in in_scadenza}
            altre: dict = defaultdict(list)
            for t in (await db.execute(
                select(Tessera).where(
                    Tessera.socio_id.in_(socio_ids),
                    Tessera.stato.in_(["attiva", "in_attesa_pagamento"]),
                )
            )).scalars().all():
                altre[t.socio_id].append(t)

            per_destinatario: dict = defaultdict(list)
            destinatari: dict = {}
            for tessera, socio in in_scadenza:
                if gia_rinnovata(tessera, altre[socio.id]):
                    continue
                destinatario, chi = socio, None
                if socio.is_minor and socio.tutore_id:
                    tutore = (await db.execute(select(Socio).where(Socio.id == socio.tutore_id))).scalar_one_or_none()
                    if tutore:
                        destinatario, chi = tutore, f"{socio.nome} {socio.cognome}"
                if not destinatario.email:
                    continue
                destinatari[destinatario.id] = destinatario
                per_destinatario[destinatario.id].append(
                    (tessera.numero_tessera, SPORT_LABEL.get(tessera.sport, tessera.sport), chi)
                )

            for dest_id, tessere in per_destinatario.items():
                d = destinatari[dest_id]
                if await invia_alert_scadenza_tessera(
                    to=d.email,
                    nome=d.nome,
                    giorni_mancanti=giorni,
                    scadenza=target.strftime("%d/%m/%Y"),
                    tessere=tessere,
                ):
                    inviati += 1
    return inviati


@celery_app.task(name="tasks.tessera_scadenza.alert_scadenza_tessera")
def alert_scadenza_tessera() -> int:
    n = asyncio.run(_invia_alert())
    if n:
        task_logger.info("Alert scadenza tessera: %d email inviate.", n)
    return n
