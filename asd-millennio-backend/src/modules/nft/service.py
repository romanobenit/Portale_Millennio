import asyncio
import time as time_module
from datetime import datetime, timezone
from uuid import UUID

import stripe
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from models.acquisto_nft import AccessoLog, AcquistoNFT, AcquistoNFTSlot
from models.slot_calendario import SlotCalendario
from models.tessera import Tessera
from models.wallet import WalletCustodiale
from modules.calendario.service import CalendarioService
from modules.nft.wallet import genera_wallet
from schemas.nft import (
    AcquistoNFTRequest,
    AcquistoNFTResponse,
    DashboardFundraisingResponse,
    NFTVerificaResponse,
)

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

TIMEOUT_FLUSSO_SECONDI = 60


class NFTService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cal_service = CalendarioService(db)

    async def _get_o_crea_wallet(self, socio_id: UUID) -> WalletCustodiale:
        result = await self.db.execute(
            select(WalletCustodiale).where(WalletCustodiale.socio_id == socio_id)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            # genera_wallet() è CPU-bound (crittografia) — non bloccare l'event loop
            address, encrypted_key = await asyncio.to_thread(genera_wallet)
            wallet = WalletCustodiale(
                socio_id=socio_id,
                wallet_address=address,
                encrypted_private_key=encrypted_key,
            )
            self.db.add(wallet)
            await self.db.flush()
            await self.db.refresh(wallet)
        return wallet

    async def _verifica_tessera_attiva(self, socio_id: UUID) -> Tessera:
        result = await self.db.execute(
            select(Tessera).where(
                Tessera.socio_id == socio_id,
                Tessera.stato == "attiva",
            )
        )
        tessera = result.scalars().first()
        if not tessera:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Tessera non attiva. Rinnova la tessera per acquistare NFT.",
            )
        return tessera

    async def avvia_acquisto(
        self, socio_id: UUID, data: AcquistoNFTRequest
    ) -> AcquistoNFTResponse:
        start = time_module.monotonic()

        tessera = await self._verifica_tessera_attiva(socio_id)

        if data.acquisto_per_minore and not data.minore_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="minore_id obbligatorio per acquisto per minore",
            )

        if data.acquisto_per_minore and data.minore_id:
            await self._verifica_tutore_minore(socio_id, data.minore_id)

        from schemas.calendario import LockRequest, OreSelezione

        lock_req = LockRequest(
            selezione=[
                OreSelezione(slot_id=item.slot_id, ore=item.ore)
                for item in data.selezione
            ]
        )
        # lock_selezione applica il lock ottimistico e calcola il prezzo in un'unica passata
        riepilogo = await self.cal_service.lock_selezione(lock_req)
        importo_eur = riepilogo.costo_totale
        slot_ids_lock = [UUID(item["slot_id"]) for item in riepilogo.selezione]
        n_slot = len(data.selezione)

        wallet = await self._get_o_crea_wallet(socio_id)

        # acquisto_id non è ancora disponibile qui (viene creato dopo la session Stripe).
        # Lo aggiungiamo come placeholder e aggiorniamo con update() dopo il flush.
        acquisto = AcquistoNFT(
            socio_id=socio_id,
            stripe_session_id="",  # verrà impostato dopo
            importo_eur=importo_eur,
            stato="in_attesa_pagamento",
            acquisto_per_minore=data.acquisto_per_minore,
            minore_id=data.minore_id,
            wallet_address=wallet.wallet_address,
        )
        self.db.add(acquisto)
        await self.db.flush()  # ottieni acquisto.id prima di creare la session Stripe

        # Stripe SDK è sincrono — eseguire in thread separato per non bloccare l'event loop
        # unit_amount: Decimal/float → centesimi interi. round() evita errori di precisione
        # floating-point (es. 50.10 * 100 = 5009.999... → int() = 5009 invece di 5010).
        unit_amount_cents = int(round(float(importo_eur) * 100))
        stripe_session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": unit_amount_cents,
                        "product_data": {
                            "name": f"Diritto d'uso Palasirion — {n_slot} slot",
                        },
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{settings.app_url}/dashboard/nft/successo?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app_url}/dashboard/nft/annullato",
            metadata={
                "socio_id": str(socio_id),
                "tessera_id": tessera.numero_tessera,
            },
            # acquisto_id nella metadata del PaymentIntent permette al webhook
            # payment_intent.payment_failed di trovare l'acquisto anche prima
            # che checkout.session.completed imposti stripe_payment_id.
            payment_intent_data={
                "metadata": {"acquisto_id": str(acquisto.id)},
            },
        )

        elapsed = time_module.monotonic() - start
        if elapsed > TIMEOUT_FLUSSO_SECONDI:
            acquisto.stato = "fallito"
            acquisto.stripe_session_id = stripe_session.id
            await self.db.flush()
            ore_da_rilasciare = {str(item.slot_id): item.ore for item in data.selezione}
            await self.cal_service.release_lock(slot_ids_lock, ore_da_rilasciare)
            await asyncio.to_thread(stripe.checkout.Session.expire, stripe_session.id)
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Timeout nel processo di acquisto. Riprova.",
            )

        # Aggiorna l'acquisto con il session_id Stripe ora che è disponibile
        acquisto.stripe_session_id = stripe_session.id
        await self.db.flush()

        for item in data.selezione:
            link = AcquistoNFTSlot(
                acquisto_nft_id=acquisto.id,
                slot_calendario_id=item.slot_id,
                ore_acquistate=item.ore,
            )
            self.db.add(link)

        await self.db.flush()

        return AcquistoNFTResponse(
            id=acquisto.id,
            stripe_session_id=stripe_session.id,
            stripe_checkout_url=stripe_session.url,
            importo_eur=importo_eur,
            slot_count=n_slot,
        )

    async def _verifica_tutore_minore(self, tutore_id: UUID, minore_id: UUID) -> None:
        from models.socio import Socio

        result = await self.db.execute(
            select(Socio).where(
                Socio.id == minore_id,
                Socio.tutore_id == tutore_id,
                Socio.is_minor.is_(True),
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Il minore specificato non risulta associato al tuo profilo",
            )

    async def conferma_pagamento(self, stripe_session_id: str) -> None:
        """Chiamato dal webhook Stripe dopo checkout.session.completed."""
        result = await self.db.execute(
            select(AcquistoNFT).where(AcquistoNFT.stripe_session_id == stripe_session_id)
        )
        acquisto = result.scalar_one_or_none()
        if not acquisto:
            logger.warning("Acquisto non trovato per session_id: %s", stripe_session_id)
            return
        if acquisto.stato != "in_attesa_pagamento":
            logger.info("Acquisto già processato: %s", stripe_session_id)
            return

        # Doppia verifica: Stripe API retrieve (sincrona → thread)
        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, stripe_session_id)
        if session.payment_status != "paid":
            acquisto.stato = "fallito"
            await self.db.flush()
            return

        acquisto.stripe_payment_id = session.payment_intent
        acquisto.stato = "pagato"
        await self.db.flush()

        from tasks.mint import esegui_mint_task

        esegui_mint_task.delay(str(acquisto.id))

    async def verifica_accesso(self, token_id: int, slot_key: str, verificato_da: UUID | None) -> NFTVerificaResponse:
        result = await self.db.execute(
            select(AcquistoNFT).where(AcquistoNFT.token_id == token_id)
        )
        acquisto = result.scalar_one_or_none()

        if not acquisto or acquisto.stato != "mintato":
            log = AccessoLog(
                token_id=token_id,
                slot_key=slot_key,
                verificato_da=verificato_da,
                esito="non_valido",
            )
            self.db.add(log)
            return NFTVerificaResponse(
                valid=False, socio=None, slot=None,
                checked_at=datetime.now(timezone.utc),
            )

        slots_link = await self.db.execute(
            select(AcquistoNFTSlot).where(AcquistoNFTSlot.acquisto_nft_id == acquisto.id)
        )
        slot_ids = [ln.slot_calendario_id for ln in slots_link.scalars().all()]
        slots = list((await self.db.execute(
            select(SlotCalendario).where(SlotCalendario.id.in_(slot_ids))
        )).scalars().all())

        data_parte, fascia_parte = slot_key.split("_", 1) if "_" in slot_key else (slot_key, "")
        slot_match = next(
            (s for s in slots if str(s.data) == data_parte and s.fascia == fascia_parte),
            None,
        )

        esito = "valido" if slot_match else "slot_errato"
        log = AccessoLog(
            token_id=token_id,
            socio_id=acquisto.socio_id,
            slot_key=slot_key,
            verificato_da=verificato_da,
            esito=esito,
        )
        self.db.add(log)
        await self.db.flush()

        return NFTVerificaResponse(
            valid=esito == "valido",
            socio=str(acquisto.socio_id),
            slot={"data": str(slot_match.data), "fascia": slot_match.fascia} if slot_match else None,
            checked_at=datetime.now(timezone.utc),
        )

    async def dashboard_fundraising(self) -> DashboardFundraisingResponse:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(AcquistoNFT.importo_eur), 0),
                func.count(AcquistoNFT.id),
            ).where(AcquistoNFT.stato == "mintato")
        )
        totale, count = result.one()

        fascia_result = await self.db.execute(
            select(SlotCalendario.fascia, func.count(SlotCalendario.id))
            .where(SlotCalendario.stato == "esaurito")
            .group_by(SlotCalendario.fascia)
        )
        per_fascia = {row[0]: row[1] for row in fascia_result.all()}

        obiettivo = float(settings.fundraising_target_eur)
        totale_float = float(totale)

        return DashboardFundraisingResponse(
            totale_raccolto_eur=totale_float,
            obiettivo_eur=obiettivo,
            percentuale=round(totale_float / obiettivo * 100, 2) if obiettivo > 0 else 0,
            nft_emessi_totali=count,
            nft_per_fascia=per_fascia,
        )
