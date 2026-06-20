from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from models.slot_calendario import SlotCalendario
from modules.calendario.pricing import PricingEngine
from schemas.calendario import DisponibilitaFascia, LockRequest, RiepilogoSelezione, SlotResponse

LOCK_DURATION_MINUTES = 30


class CalendarioService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def lista_slot(
        self,
        data_inizio: date | None,
        data_fine: date | None,
        fascia: str | None,
        page: int,
        limit: int,
    ) -> list[SlotResponse]:
        q = select(SlotCalendario)
        if data_inizio:
            q = q.where(SlotCalendario.data >= data_inizio)
        if data_fine:
            q = q.where(SlotCalendario.data <= data_fine)
        if fascia:
            q = q.where(SlotCalendario.fascia == fascia)
        # Solo Lun-Ven
        q = q.order_by(SlotCalendario.data, SlotCalendario.fascia)
        q = q.offset((page - 1) * limit).limit(limit)

        result = await self.db.execute(q)
        slots = list(result.scalars().all())

        now = datetime.now(timezone.utc)
        for slot in slots:
            if slot.stato == "bloccato" and slot.bloccato_fino_a and slot.bloccato_fino_a < now:
                await self._rilascia_lock(slot)

        return [SlotResponse.model_validate(s) for s in slots]

    async def get_slot(self, slot_id: UUID) -> SlotCalendario:
        result = await self.db.execute(
            select(SlotCalendario).where(SlotCalendario.id == slot_id)
        )
        slot = result.scalar_one_or_none()
        if not slot:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Slot non trovato")
        return slot

    async def disponibilita(self, data_inizio: date, data_fine: date) -> list[DisponibilitaFascia]:
        """Restituisce disponibilità e prezzo/ora per ogni slot nel periodo."""
        result = await self.db.execute(
            select(SlotCalendario).where(
                and_(
                    SlotCalendario.data >= data_inizio,
                    SlotCalendario.data <= data_fine,
                )
            ).order_by(SlotCalendario.data, SlotCalendario.fascia)
        )
        slots = list(result.scalars().all())
        engine = PricingEngine(self.db)
        out: list[DisponibilitaFascia] = []
        for slot in slots:
            now = datetime.now(timezone.utc)
            if slot.stato == "bloccato" and slot.bloccato_fino_a and slot.bloccato_fino_a < now:
                await self._rilascia_lock(slot)

            pricing = await engine.calcola_prezzo_ora(slot.fascia, slot.data)
            ore_vendute = slot.ore_vendute or []
            ore_in_lock = slot.ore_in_lock or []
            # Tutte le ore della fascia
            h_inizio = slot.ora_inizio.hour
            ore_fascia = list(range(h_inizio, h_inizio + slot.ore_totali))
            ore_libere = [h for h in ore_fascia if h not in ore_vendute and h not in ore_in_lock]

            out.append(DisponibilitaFascia(
                slot_id=slot.id,
                data=slot.data,
                fascia=slot.fascia,
                ora_inizio=slot.ora_inizio,
                ora_fine=slot.ora_fine,
                ore_totali=slot.ore_totali,
                ore_vendute=ore_vendute,
                ore_in_lock=ore_in_lock,
                ore_libere=ore_libere,
                stato=slot.stato,
                prezzo_ora=pricing["prezzo_ora"],
                moltiplicatore_data=pricing["moltiplicatore_data"],
                moltiplicatore_scarsita=pricing["moltiplicatore_scarsita"],
                sconto_promo_pct=pricing["sconto_promo_pct"],
            ))
        return out

    async def lock_selezione(self, req: LockRequest) -> RiepilogoSelezione:
        """
        Blocca le ore selezionate e calcola il prezzo con il motore dinamico.
        Raise 409 se un'ora è già venduta o in lock da altro utente.
        """
        now = datetime.now(timezone.utc)
        scadenza_lock = now + timedelta(minutes=LOCK_DURATION_MINUTES)

        selezione_engine: list[dict] = []

        # Ordine deterministico: previene deadlock tra transazioni concorrenti
        # che acquisiscono gli stessi slot in ordine inverso.
        selezione_ordinata = sorted(req.selezione, key=lambda i: str(i.slot_id))

        for item in selezione_ordinata:
            result = await self.db.execute(
                select(SlotCalendario)
                .where(SlotCalendario.id == item.slot_id)
                .with_for_update()
            )
            slot = result.scalar_one_or_none()
            if not slot:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Slot non trovato: {item.slot_id}")

            # Rilascia eventuali lock scaduti
            if slot.stato == "bloccato" and slot.bloccato_fino_a and slot.bloccato_fino_a < now:
                await self._rilascia_lock(slot)

            ore_vendute = set(slot.ore_vendute or [])
            ore_in_lock = set(slot.ore_in_lock or [])

            for h in item.ore:
                if h in ore_vendute:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        detail=f"Ora {h}:00 del {slot.data} già venduta",
                    )
                if h in ore_in_lock:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        detail=f"Ora {h}:00 del {slot.data} temporaneamente in lock da altro acquirente",
                    )

            # Applica lock
            nuove_ore_lock = sorted(ore_in_lock | set(item.ore))
            slot.ore_in_lock = nuove_ore_lock
            slot.bloccato_fino_a = scadenza_lock
            slot.stato = self._calcola_stato(slot)

            selezione_engine.append({"slot": slot, "ore": list(item.ore)})

        await self.db.flush()

        engine = PricingEngine(self.db)
        riepilogo = await engine.calcola_prezzo_selezione(selezione_engine)

        return RiepilogoSelezione(
            selezione=[{"slot_id": str(i["slot"].id), "ore": i["ore"]} for i in selezione_engine],
            ore_notte=riepilogo["ore_notte"],
            ore_mattina=riepilogo["ore_mattina"],
            ore_pomeriggio=riepilogo["ore_pomeriggio"],
            costo_totale=riepilogo["costo_totale"],
            dettaglio=riepilogo["dettaglio"],
        )

    async def release_lock(self, slot_ids: list[UUID], ore_da_rilasciare: dict[str, list[int]]) -> None:
        result = await self.db.execute(
            select(SlotCalendario).where(SlotCalendario.id.in_(slot_ids))
        )
        for slot in result.scalars().all():
            da_rimuovere = set(ore_da_rilasciare.get(str(slot.id), []))
            slot.ore_in_lock = [h for h in (slot.ore_in_lock or []) if h not in da_rimuovere]
            if not slot.ore_in_lock:
                slot.bloccato_fino_a = None
            slot.stato = self._calcola_stato(slot)
        await self.db.flush()

    async def mark_ore_vendute(self, slot_id: UUID, ore: list[int], token_id: int) -> None:
        result = await self.db.execute(
            select(SlotCalendario).where(SlotCalendario.id == slot_id)
        )
        slot = result.scalar_one_or_none()
        if not slot:
            logger.warning("mark_ore_vendute: slot %s non trovato", slot_id)
            return
        # Sposta le ore da in_lock a vendute
        vendute = set(slot.ore_vendute or []) | set(ore)
        in_lock = set(slot.ore_in_lock or []) - set(ore)
        slot.ore_vendute = sorted(vendute)
        slot.ore_in_lock = sorted(in_lock)
        slot.nft_token_id = token_id
        if not slot.ore_in_lock:
            slot.bloccato_fino_a = None
        slot.stato = self._calcola_stato(slot)
        await self.db.flush()

    async def calcola_prezzo(self, selezione: list[dict]) -> RiepilogoSelezione:
        """Calcola il prezzo senza applicare lock (per anteprima)."""
        engine = PricingEngine(self.db)
        riepilogo = await engine.calcola_prezzo_selezione(selezione)
        return RiepilogoSelezione(
            selezione=[{"slot_id": str(i["slot"].id), "ore": i["ore"]} for i in selezione],
            ore_notte=riepilogo["ore_notte"],
            ore_mattina=riepilogo["ore_mattina"],
            ore_pomeriggio=riepilogo["ore_pomeriggio"],
            costo_totale=riepilogo["costo_totale"],
            dettaglio=riepilogo["dettaglio"],
        )

    @staticmethod
    def _calcola_stato(slot: SlotCalendario) -> str:
        vendute = set(slot.ore_vendute or [])
        in_lock = set(slot.ore_in_lock or [])
        h_inizio = slot.ora_inizio.hour
        ore_fascia = set(range(h_inizio, h_inizio + slot.ore_totali))

        if vendute >= ore_fascia:
            return "esaurito"
        occupate = vendute | in_lock
        if occupate >= ore_fascia:
            # Tutto occupato: combinazione venduto+lock esaurisce la fascia
            return "bloccato"
        if in_lock:
            # Parte in lock, il resto libero o venduto
            return "bloccato"
        if vendute:
            return "parziale"
        return "libero"

    @staticmethod
    async def _rilascia_lock(slot: SlotCalendario) -> None:
        slot.ore_in_lock = []
        slot.bloccato_fino_a = None
        slot.stato = CalendarioService._calcola_stato(slot)
