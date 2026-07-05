from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import List
from uuid import UUID

import stripe
from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from models.prenotazione_campo import PrenotazioneCampo
from models.slot_template_campo import SlotTemplateCampo
from models.tessera import Tessera
from schemas.campi import (
    CheckoutCarrelloResponse,
    GiornoDisponibileResponse,
    PrenotazioneCampoResponse,
)

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

LOCK_MINUTES = 30
CANCELLATION_HOURS_BEFORE = 24
GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]


class CampiService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _slot_ore(tmpl: SlotTemplateCampo) -> List[tuple[time, time]]:
        """Divide la finestra del template in slot da 1 ora (16:30–19:30 → 3 slot)."""
        slots: List[tuple[time, time]] = []
        cur = datetime.combine(date.min, tmpl.ora_inizio)
        end = datetime.combine(date.min, tmpl.ora_fine)
        while cur + timedelta(hours=1) <= end:
            nxt = cur + timedelta(hours=1)
            slots.append((cur.time(), nxt.time()))
            cur = nxt
        return slots

    async def _bookings_attive(self, template_id: UUID, data: date):
        """Prenotazioni attive (confermate o in lock non scaduto) per template+data."""
        now = datetime.now(timezone.utc)
        r = await self.db.execute(
            select(
                PrenotazioneCampo.campo,
                PrenotazioneCampo.ora_inizio,
                PrenotazioneCampo.ora_fine,
            ).where(
                and_(
                    PrenotazioneCampo.template_id == template_id,
                    PrenotazioneCampo.data == data,
                    PrenotazioneCampo.stato.in_(["bloccata", "confermata"]),
                    (
                        (PrenotazioneCampo.stato == "confermata")
                        | (PrenotazioneCampo.bloccata_fino_a > now)
                    ),
                )
            )
        )
        return r.all()

    @staticmethod
    def _campi_occupati_slot(bookings, slot_inizio: time, slot_fine: time) -> set:
        return {b.campo for b in bookings if b.ora_inizio < slot_fine and b.ora_fine > slot_inizio}

    def _importo_ora(self, tmpl: SlotTemplateCampo) -> Decimal:
        return Decimal(tmpl.costo_ora).quantize(Decimal("0.01"))

    async def _verifica_tessera(self, socio_id: UUID) -> None:
        r = await self.db.execute(
            select(Tessera).where(and_(Tessera.socio_id == socio_id, Tessera.stato == "attiva"))
        )
        if not r.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Tessera non attiva — impossibile prenotare il campo",
            )

    async def _scadi_lock_socio(self, socio_id: UUID) -> None:
        """Annulla (stato=scaduta) i lock del socio non pagati e scaduti.
        È il meccanismo 'fine sessione': se non si paga entro il lock, si rilascia."""
        now = datetime.now(timezone.utc)
        r = await self.db.execute(
            select(PrenotazioneCampo).where(
                and_(
                    PrenotazioneCampo.socio_id == socio_id,
                    PrenotazioneCampo.stato == "bloccata",
                    PrenotazioneCampo.bloccata_fino_a <= now,
                )
            )
        )
        scadute = r.scalars().all()
        for p in scadute:
            p.stato = "scaduta"
        if scadute:
            await self.db.flush()

    # ─── disponibilità (per singola ora) ────────────────────────────────────

    async def lista_disponibilita(
        self, data_inizio: date, data_fine: date
    ) -> List[GiornoDisponibileResponse]:
        """Ogni slot da 1 ora prenotabile con i campi liberi in quell'ora."""
        r = await self.db.execute(
            select(SlotTemplateCampo).where(
                and_(
                    SlotTemplateCampo.attivo == True,  # noqa: E712
                    SlotTemplateCampo.valido_dal <= data_fine,
                    SlotTemplateCampo.valido_fino_al >= data_inizio,
                )
            )
        )
        templates = r.scalars().all()

        result: List[GiornoDisponibileResponse] = []
        current = data_inizio
        while current <= data_fine:
            for tmpl in templates:
                if current.weekday() != tmpl.giorno_settimana:
                    continue
                if current < tmpl.valido_dal or current > tmpl.valido_fino_al:
                    continue
                bookings = await self._bookings_attive(tmpl.id, current)
                for slot_inizio, slot_fine in self._slot_ore(tmpl):
                    occupati = self._campi_occupati_slot(bookings, slot_inizio, slot_fine)
                    disponibili = tmpl.num_campi - len(occupati)
                    result.append(
                        GiornoDisponibileResponse(
                            data=current,
                            template_id=tmpl.id,
                            giorno_settimana=tmpl.giorno_settimana,
                            ora_inizio=slot_inizio,
                            ora_fine=slot_fine,
                            campi_totali=tmpl.num_campi,
                            campi_disponibili=disponibili,
                            costo_ora=tmpl.costo_ora,
                            durata_ore=1,
                            importo_totale=self._importo_ora(tmpl),
                            sport=tmpl.sport or [],
                        )
                    )
            current += timedelta(days=1)

        return result

    # ─── carrello: aggiungi 1 ora (lock, nessun pagamento) ──────────────────

    async def aggiungi_al_carrello(
        self, socio_id: UUID, template_id: UUID, data: date, ora_inizio: time
    ) -> PrenotazioneCampoResponse:
        await self._verifica_tessera(socio_id)
        # Lock del template: serializza l'assegnazione dei campi (no race).
        tmpl = (
            await self.db.execute(
                select(SlotTemplateCampo).where(SlotTemplateCampo.id == template_id).with_for_update()
            )
        ).scalar_one_or_none()
        if not tmpl:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template non trovato")
        if not tmpl.attivo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Template non attivo")
        if data.weekday() != tmpl.giorno_settimana:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="La data non corrisponde al giorno del template")
        if data < tmpl.valido_dal or data > tmpl.valido_fino_al:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Data fuori dal periodo del template")

        slot = next((s for s in self._slot_ore(tmpl) if s[0] == ora_inizio), None)
        if slot is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Ora non valida per questa fascia")
        slot_inizio, slot_fine = slot

        bookings = await self._bookings_attive(template_id, data)
        occupati = self._campi_occupati_slot(bookings, slot_inizio, slot_fine)
        campo = next((c for c in range(1, tmpl.num_campi + 1) if c not in occupati), None)
        if campo is None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Nessun campo disponibile per questa ora")

        now = datetime.now(timezone.utc)
        prenotazione = PrenotazioneCampo(
            socio_id=socio_id,
            template_id=template_id,
            data=data,
            ora_inizio=slot_inizio,
            ora_fine=slot_fine,
            campo=campo,
            importo_eur=self._importo_ora(tmpl),
            stato="bloccata",
            bloccata_fino_a=now + timedelta(minutes=LOCK_MINUTES),
            cancellabile_fino_a=(
                datetime.combine(data, slot_inizio).replace(tzinfo=timezone.utc)
                - timedelta(hours=CANCELLATION_HOURS_BEFORE)
            ),
        )
        self.db.add(prenotazione)
        await self.db.flush()
        await self.db.refresh(prenotazione)
        logger.info("Ora aggiunta al carrello: socio=%s data=%s ora=%s campo=%s", socio_id, data, slot_inizio, campo)
        return PrenotazioneCampoResponse.model_validate(prenotazione)

    async def lista_carrello(self, socio_id: UUID) -> List[PrenotazioneCampoResponse]:
        """Ore bloccate (non pagate, lock non scaduto) del socio = carrello."""
        await self._scadi_lock_socio(socio_id)
        now = datetime.now(timezone.utc)
        r = await self.db.execute(
            select(PrenotazioneCampo)
            .where(
                and_(
                    PrenotazioneCampo.socio_id == socio_id,
                    PrenotazioneCampo.stato == "bloccata",
                    PrenotazioneCampo.bloccata_fino_a > now,
                )
            )
            .order_by(PrenotazioneCampo.data, PrenotazioneCampo.ora_inizio)
        )
        return [PrenotazioneCampoResponse.model_validate(p) for p in r.scalars().all()]

    # ─── checkout: paga tutto il carrello in una volta ──────────────────────

    async def checkout_carrello(self, socio_id: UUID) -> CheckoutCarrelloResponse:
        await self._scadi_lock_socio(socio_id)
        now = datetime.now(timezone.utc)
        r = await self.db.execute(
            select(PrenotazioneCampo, SlotTemplateCampo)
            .join(SlotTemplateCampo, PrenotazioneCampo.template_id == SlotTemplateCampo.id)
            .where(
                and_(
                    PrenotazioneCampo.socio_id == socio_id,
                    PrenotazioneCampo.stato == "bloccata",
                    PrenotazioneCampo.bloccata_fino_a > now,
                )
            )
            .order_by(PrenotazioneCampo.data, PrenotazioneCampo.ora_inizio)
        )
        rows = r.all()
        if not rows:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Carrello vuoto")

        line_items = []
        importo_totale = Decimal("0")
        for pren, tmpl in rows:
            importo_totale += Decimal(pren.importo_eur)
            giorno_str = GIORNI[pren.data.weekday()]
            sport_str = " / ".join(tmpl.sport) if tmpl.sport else "Campo"
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "unit_amount": int(Decimal(pren.importo_eur) * 100),
                    "product_data": {
                        "name": f"Campo {pren.campo} — {sport_str} — {giorno_str} {pren.data.strftime('%d/%m/%Y')}",
                        "description": f"{pren.ora_inizio.strftime('%H:%M')}–{pren.ora_fine.strftime('%H:%M')} · Campo {pren.campo}",
                    },
                },
                "quantity": 1,
            })

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url=f"{settings.app_url}/dashboard/prenotazioni?status=success",
            cancel_url=f"{settings.app_url}/dashboard/prenotazioni?status=cancel",
            metadata={"tipo": "prenotazione_campo", "socio_id": str(socio_id)},
        )

        # Stessa sessione su tutte le prenotazioni del carrello (1 pagamento).
        for pren, _ in rows:
            pren.stripe_session_id = session["id"]
        await self.db.flush()

        logger.info("Checkout carrello: socio=%s slot=%s totale=%s", socio_id, len(rows), importo_totale)
        return CheckoutCarrelloResponse(
            stripe_checkout_url=session["url"],
            importo_totale=importo_totale.quantize(Decimal("0.01")),
            num_slot=len(rows),
        )

    async def conferma_pagamento(self, stripe_session_id: str) -> None:
        """Conferma TUTTE le prenotazioni collegate alla sessione Stripe (carrello)."""
        r = await self.db.execute(
            select(PrenotazioneCampo).where(PrenotazioneCampo.stripe_session_id == stripe_session_id)
        )
        prenotazioni = r.scalars().all()
        if not prenotazioni:
            logger.warning("conferma_pagamento: nessuna prenotazione per session %s", stripe_session_id)
            return
        for pren in prenotazioni:
            if pren.stato == "confermata":
                continue
            pren.stato = "confermata"
            pren.bloccata_fino_a = None
        await self.db.flush()
        logger.info("Prenotazioni campo confermate: %s (session %s)", len(prenotazioni), stripe_session_id)

    # ─── cancellazione (carrello o confermata) ──────────────────────────────

    async def cancella_prenotazione(
        self, socio_id: UUID, prenotazione_id: UUID
    ) -> PrenotazioneCampoResponse:
        r = await self.db.execute(
            select(PrenotazioneCampo).where(
                and_(PrenotazioneCampo.id == prenotazione_id, PrenotazioneCampo.socio_id == socio_id)
            )
        )
        pren = r.scalar_one_or_none()
        if not pren:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Prenotazione non trovata")

        if pren.stato == "bloccata":
            # rimozione dal carrello (non ancora pagata)
            pren.stato = "cancellata"
            await self.db.flush()
            await self.db.refresh(pren)
            logger.info("Ora rimossa dal carrello: id=%s", pren.id)
            return PrenotazioneCampoResponse.model_validate(pren)

        if pren.stato != "confermata":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Questa prenotazione non può essere cancellata",
            )

        now = datetime.now(timezone.utc)
        if pren.cancellabile_fino_a and now > pren.cancellabile_fino_a:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Impossibile cancellare: il limite di cancellazione è scaduto",
            )
        pren.stato = "cancellata"
        await self.db.flush()
        await self.db.refresh(pren)
        logger.info("Prenotazione campo cancellata: id=%s", pren.id)
        return PrenotazioneCampoResponse.model_validate(pren)

    async def lista_prenotazioni_socio(self, socio_id: UUID) -> List[PrenotazioneCampoResponse]:
        """Solo prenotazioni CONFERMATE (pagate)."""
        r = await self.db.execute(
            select(PrenotazioneCampo)
            .where(
                and_(
                    PrenotazioneCampo.socio_id == socio_id,
                    PrenotazioneCampo.stato == "confermata",
                )
            )
            .order_by(PrenotazioneCampo.data, PrenotazioneCampo.ora_inizio)
        )
        return [PrenotazioneCampoResponse.model_validate(p) for p in r.scalars().all()]
