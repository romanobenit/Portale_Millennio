from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List
from uuid import UUID

import stripe
from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from models.prenotazione_campo import PrenotazioneCampo
from models.slot_template_campo import SlotTemplateCampo
from models.tessera import Tessera
from schemas.campi import (
    CheckoutCampoResponse,
    GiornoDisponibileResponse,
    PrenotazioneCampoResponse,
)

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

LOCK_MINUTES = 30
CANCELLATION_HOURS_BEFORE = 24


class CampiService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── helpers ────────────────────────────────────────────────────────────

    async def _get_template(self, template_id: UUID) -> SlotTemplateCampo:
        r = await self.db.execute(
            select(SlotTemplateCampo).where(SlotTemplateCampo.id == template_id)
        )
        tmpl = r.scalar_one_or_none()
        if not tmpl:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template non trovato")
        return tmpl

    async def _campi_occupati(self, template_id: UUID, data: date) -> List[int]:
        """Campi già prenotati (confermati o in lock attivo) per un dato template+data."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(PrenotazioneCampo.campo).where(
                and_(
                    PrenotazioneCampo.template_id == template_id,
                    PrenotazioneCampo.data == data,
                    PrenotazioneCampo.stato.in_(["bloccata", "confermata"]),
                    # esclude lock scaduti
                    (
                        (PrenotazioneCampo.stato == "confermata")
                        | (PrenotazioneCampo.bloccata_fino_a > now)
                    ),
                )
            )
        )
        return [row[0] for row in result.all()]

    async def _assegna_campo(self, template_id: UUID, data: date, num_campi: int) -> int:
        occupati = await self._campi_occupati(template_id, data)
        for c in range(1, num_campi + 1):
            if c not in occupati:
                return c
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Nessun campo disponibile per questa fascia")

    def _calcola_importo(self, tmpl: SlotTemplateCampo) -> Decimal:
        inizio = datetime.combine(date.today(), tmpl.ora_inizio)
        fine = datetime.combine(date.today(), tmpl.ora_fine)
        ore = Decimal(str((fine - inizio).seconds / 3600))
        return (ore * tmpl.costo_ora).quantize(Decimal("0.01"))

    async def _verifica_tessera(self, socio_id: UUID) -> None:
        r = await self.db.execute(
            select(Tessera).where(
                and_(
                    Tessera.socio_id == socio_id,
                    Tessera.stato == "attiva",
                )
            )
        )
        if not r.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Tessera non attiva — impossibile prenotare il campo",
            )

    # ─── disponibilità ──────────────────────────────────────────────────────

    async def lista_disponibilita(
        self,
        data_inizio: date,
        data_fine: date,
    ) -> List[GiornoDisponibileResponse]:
        """
        Restituisce tutti i giorni disponibili nell'intervallo per ogni template attivo.
        """
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
                if current.weekday() == tmpl.giorno_settimana:
                    if current < tmpl.valido_dal or current > tmpl.valido_fino_al:
                        continue
                    occupati = await self._campi_occupati(tmpl.id, current)
                    disponibili = tmpl.num_campi - len(occupati)
                    if disponibili <= 0:
                        continue
                    importo = self._calcola_importo(tmpl)
                    inizio_dt = datetime.combine(date.today(), tmpl.ora_inizio)
                    fine_dt = datetime.combine(date.today(), tmpl.ora_fine)
                    durata = int((fine_dt - inizio_dt).seconds / 3600)
                    result.append(
                        GiornoDisponibileResponse(
                            data=current,
                            template_id=tmpl.id,
                            giorno_settimana=tmpl.giorno_settimana,
                            ora_inizio=tmpl.ora_inizio,
                            ora_fine=tmpl.ora_fine,
                            campi_totali=tmpl.num_campi,
                            campi_disponibili=disponibili,
                            costo_ora=tmpl.costo_ora,
                            durata_ore=durata,
                            importo_totale=importo,
                            sport=tmpl.sport or [],
                        )
                    )
            current += timedelta(days=1)

        return result

    # ─── prenotazione ───────────────────────────────────────────────────────

    async def avvia_prenotazione(
        self,
        socio_id: UUID,
        template_id: UUID,
        data: date,
    ) -> CheckoutCampoResponse:
        await self._verifica_tessera(socio_id)
        tmpl = await self._get_template(template_id)

        if not tmpl.attivo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Template non attivo")
        if data.weekday() != tmpl.giorno_settimana:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="La data selezionata non corrisponde al giorno del template",
            )
        if data < tmpl.valido_dal or data > tmpl.valido_fino_al:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Data fuori dal periodo del template")

        campo = await self._assegna_campo(template_id, data, tmpl.num_campi)
        importo = self._calcola_importo(tmpl)

        now = datetime.now(timezone.utc)
        bloccata_fino_a = now + timedelta(minutes=LOCK_MINUTES)
        cancellabile_fino_a = datetime.combine(data, tmpl.ora_inizio) - timedelta(hours=CANCELLATION_HOURS_BEFORE)
        # Make timezone-aware
        cancellabile_fino_a = cancellabile_fino_a.replace(tzinfo=timezone.utc)

        prenotazione = PrenotazioneCampo(
            socio_id=socio_id,
            template_id=template_id,
            data=data,
            ora_inizio=tmpl.ora_inizio,
            ora_fine=tmpl.ora_fine,
            campo=campo,
            importo_eur=importo,
            stato="bloccata",
            bloccata_fino_a=bloccata_fino_a,
            cancellabile_fino_a=cancellabile_fino_a,
        )
        self.db.add(prenotazione)
        await self.db.flush()

        importo_centesimi = int(importo * 100)
        giorno_str = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"][data.weekday()]
        sport_str = " / ".join(tmpl.sport) if tmpl.sport else "Campo"

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": importo_centesimi,
                    "product_data": {
                        "name": f"Campo {campo} — {sport_str} — {giorno_str} {data.strftime('%d/%m/%Y')}",
                        "description": (
                            f"{tmpl.ora_inizio.strftime('%H:%M')}–{tmpl.ora_fine.strftime('%H:%M')} "
                            f"· Campo {campo}"
                        ),
                    },
                },
                "quantity": 1,
            }],
            success_url=f"{settings.app_url}/dashboard/prenotazioni?status=success",
            cancel_url=f"{settings.app_url}/dashboard/prenotazioni?status=cancel",
            metadata={
                "tipo": "prenotazione_campo",
                "prenotazione_id": str(prenotazione.id),
            },
        )

        prenotazione.stripe_session_id = session["id"]
        await self.db.flush()

        logger.info(
            "Prenotazione campo avviata: id=%s campo=%s data=%s importo=%s",
            prenotazione.id,
            campo,
            data,
            importo,
        )

        return CheckoutCampoResponse(
            prenotazione_id=prenotazione.id,
            stripe_checkout_url=session["url"],
            campo=campo,
            importo_eur=importo,
            bloccata_fino_a=bloccata_fino_a,
        )

    async def conferma_pagamento(self, stripe_session_id: str) -> None:
        r = await self.db.execute(
            select(PrenotazioneCampo).where(
                PrenotazioneCampo.stripe_session_id == stripe_session_id
            )
        )
        pren = r.scalar_one_or_none()
        if not pren:
            logger.warning("conferma_pagamento: prenotazione non trovata per session %s", stripe_session_id)
            return
        if pren.stato == "confermata":
            return
        pren.stato = "confermata"
        pren.bloccata_fino_a = None
        await self.db.flush()
        logger.info("Prenotazione campo confermata: id=%s campo=%s data=%s", pren.id, pren.campo, pren.data)

    async def cancella_prenotazione(
        self,
        socio_id: UUID,
        prenotazione_id: UUID,
    ) -> PrenotazioneCampoResponse:
        r = await self.db.execute(
            select(PrenotazioneCampo).where(
                and_(
                    PrenotazioneCampo.id == prenotazione_id,
                    PrenotazioneCampo.socio_id == socio_id,
                )
            )
        )
        pren = r.scalar_one_or_none()
        if not pren:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Prenotazione non trovata")

        now = datetime.now(timezone.utc)
        if pren.stato != "confermata":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Solo le prenotazioni confermate possono essere cancellate",
            )
        if pren.cancellabile_fino_a and now > pren.cancellabile_fino_a:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Impossibile cancellare: il limite di cancellazione è scaduto",
            )

        pren.stato = "cancellata"
        await self.db.flush()
        logger.info("Prenotazione campo cancellata: id=%s", pren.id)
        return PrenotazioneCampoResponse.model_validate(pren)

    async def lista_prenotazioni_socio(self, socio_id: UUID) -> List[PrenotazioneCampoResponse]:
        r = await self.db.execute(
            select(PrenotazioneCampo)
            .where(
                and_(
                    PrenotazioneCampo.socio_id == socio_id,
                    PrenotazioneCampo.stato.in_(["bloccata", "confermata"]),
                )
            )
            .order_by(PrenotazioneCampo.data)
        )
        return [PrenotazioneCampoResponse.model_validate(p) for p in r.scalars().all()]
