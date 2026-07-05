"""
Seed slot calendario per il periodo di vendita Palasirio.

Genera UN ROW PER (data, fascia) per ogni Lunedì–Venerdì
nel periodo 01/01/2027 – 31/12/2042.

Fasce orarie vendibili (00:00–14:59):
  notte      00:00–07:59  ore_totali=8
  mattina    08:00–12:59  ore_totali=5
  pomeriggio 13:00–14:59  ore_totali=2

Idempotente: usa UNIQUE(data, fascia) — non duplica.

Uso:
  cd asd-millennio-backend
  python src/scripts/seed_slot_calendario.py [--dry-run]
"""
import asyncio
import sys
import uuid
from datetime import date, time, timedelta

from sqlalchemy import select

sys.path.insert(0, "src")

from core.config import get_settings  # noqa: E402
from core.database import AsyncSessionLocal  # noqa: E402
from models.slot_calendario import SlotCalendario  # noqa: E402

settings = get_settings()

# Lun=0 Mar=1 Mer=2 Gio=3 Ven=4 — Sab e Dom non vendibili
GIORNI_VENDIBILI = {0, 1, 2, 3, 4}

# (fascia, ora_inizio, ora_fine, ore_totali)
FASCE: list[tuple[str, time, time, int]] = [
    ("notte",      time(0, 0),  time(7, 59),  8),
    ("mattina",    time(8, 0),  time(12, 59), 5),
    ("pomeriggio", time(13, 0), time(14, 59), 2),
]

STAGIONE_INIZIO = date(2027, 1, 1)
STAGIONE_FINE   = date(2042, 12, 31)


async def _seed(dry_run: bool = False) -> None:
    # Raccoglie tutti i giorni vendibili della stagione
    date_vendibili: list[date] = []
    giorno = STAGIONE_INIZIO
    while giorno <= STAGIONE_FINE:
        if giorno.weekday() in GIORNI_VENDIBILI:
            date_vendibili.append(giorno)
        giorno += timedelta(days=1)

    totale_atteso = len(date_vendibili) * len(FASCE)
    print(
        f"Periodo vendita Palasirio {STAGIONE_INIZIO} -> {STAGIONE_FINE}: "
        f"{len(date_vendibili)} giorni vendibili (Lun–Ven) × {len(FASCE)} fasce "
        f"= {totale_atteso} slot totali"
    )

    async with AsyncSessionLocal() as db:
        esistenti_result = await db.execute(
            select(SlotCalendario.data, SlotCalendario.fascia)
        )
        esistenti: set[tuple] = {(r.data, r.fascia) for r in esistenti_result}

        nuovi = 0
        saltati = 0
        da_inserire: list[SlotCalendario] = []

        for giorno in date_vendibili:
            for fascia, ora_inizio, ora_fine, ore_totali in FASCE:
                if (giorno, fascia) in esistenti:
                    saltati += 1
                    continue

                slot = SlotCalendario(
                    id=uuid.uuid4(),
                    data=giorno,
                    fascia=fascia,
                    ora_inizio=ora_inizio,
                    ora_fine=ora_fine,
                    ore_totali=ore_totali,
                    ore_vendute=[],
                    ore_in_lock=[],
                    stato="libero",
                )
                da_inserire.append(slot)
                nuovi += 1

        print(f"  Nuovi da inserire: {nuovi}  |  Già esistenti (saltati): {saltati}")

        if dry_run:
            print("  [DRY-RUN] Nessun dato scritto.")
            return

        if da_inserire:
            db.add_all(da_inserire)
            await db.commit()
            print(f"  OK: {nuovi} slot inseriti.")
        else:
            print("  Nessun nuovo slot da inserire — DB già aggiornato.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    asyncio.run(_seed(dry_run=dry))
