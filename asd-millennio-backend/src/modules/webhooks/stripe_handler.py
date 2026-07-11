import asyncio
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import get_db
from core.logger import logger
from core.rate_limit import limiter
from models.webhook_log import WebhookLog
from modules.nft.service import NFTService

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
@limiter.limit("200/minute")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        # construct_event è sincrono — thread per non bloccare l'event loop
        event = await asyncio.to_thread(
            stripe.Webhook.construct_event,
            payload,
            sig_header,
            settings.stripe_webhook_secret,
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Firma webhook non valida")
    except Exception as e:
        logger.error("Errore nel parsing del webhook Stripe: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Payload non valido")

    event_id = event["id"]

    existing = await db.execute(
        select(WebhookLog).where(WebhookLog.webhook_id == event_id)
    )
    if existing.scalar_one_or_none():
        logger.info("Webhook già processato (idempotency): %s", event_id)
        return {"status": "already_processed"}

    log = WebhookLog(
        webhook_id=event_id,
        event_type=event["type"],
        # Riusa il body grezzo già letto: gli oggetti stripe.Event non supportano
        # dict() in modo affidabile tra versioni dell'SDK (KeyError: 0).
        payload=payload.decode("utf-8"),
        processed=False,
    )
    db.add(log)
    await db.flush()

    nft_service = NFTService(db)
    event_type = event["type"]
    acq_to_mint = None  # id acquisto da accodare DOPO il commit (no enqueue-before-commit)

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        # stripe.StripeObject (stripe-python >= 7) non supporta .get() — serve to_dict().
        tipo = (session.to_dict().get("metadata") or {}).get("tipo", "nft")
        if tipo == "prenotazione_campo":
            from modules.campi.service import CampiService
            await CampiService(db).conferma_pagamento(session_id)
        else:
            acq_to_mint = await nft_service.conferma_pagamento(session_id)

    elif event_type == "checkout.session.expired":
        await nft_service.gestisci_sessione_scaduta(event["data"]["object"]["id"])

    elif event_type == "payment_intent.payment_failed":
        pi_id = event["data"]["object"]["id"]
        logger.warning("Pagamento fallito: %s", pi_id)
        # stripe_payment_id viene impostato solo da checkout.session.completed (successo),
        # quindi non è disponibile qui. Usiamo acquisto_id dalla metadata del PaymentIntent
        # (impostata in avvia_acquisto() via payment_intent_data.metadata).
        from models.acquisto_nft import AcquistoNFT, AcquistoNFTSlot
        from models.slot_calendario import SlotCalendario
        acquisto_id_meta = event["data"]["object"].to_dict().get("metadata", {}).get("acquisto_id")
        acquisto = None
        if acquisto_id_meta:
            try:
                from uuid import UUID as _UUID
                result = await db.execute(
                    select(AcquistoNFT).where(AcquistoNFT.id == _UUID(acquisto_id_meta))
                )
                acquisto = result.scalar_one_or_none()
            except Exception as meta_err:
                logger.error("Errore lettura acquisto_id da metadata PaymentIntent: %s", meta_err)
        if not acquisto_id_meta:
            logger.warning("payment_intent.payment_failed: acquisto_id mancante in metadata per PI %s", pi_id)
        if acquisto and acquisto.stato == "in_attesa_pagamento":
            acquisto.stato = "fallito"
            links = await db.execute(
                select(AcquistoNFTSlot).where(AcquistoNFTSlot.acquisto_nft_id == acquisto.id)
            )
            slot_ids = [ln.slot_calendario_id for ln in links.scalars().all()]
            if slot_ids:
                slots_res = await db.execute(
                    select(SlotCalendario).where(SlotCalendario.id.in_(slot_ids))
                )
                for slot in slots_res.scalars().all():
                    slot.ore_in_lock = []
                    slot.bloccato_fino_a = None
                    h_inizio = slot.ora_inizio.hour
                    ore_fascia = set(range(h_inizio, h_inizio + slot.ore_totali))
                    slot.stato = (
                        "esaurito" if set(slot.ore_vendute or []) >= ore_fascia
                        else "parziale" if slot.ore_vendute
                        else "libero"
                    )
            await db.flush()

    elif event_type == "charge.refunded":
        charge_obj = event["data"]["object"]
        charge_id = charge_obj["id"]
        # stripe_payment_id salva il PaymentIntent ID (pi_xxx), non il charge ID (ch_xxx).
        # Il campo payment_intent nella charge object collega i due.
        pi_id_from_charge = charge_obj.to_dict().get("payment_intent")
        logger.info("Rimborso ricevuto: charge=%s pi=%s", charge_id, pi_id_from_charge)
        from models.acquisto_nft import AcquistoNFT, AcquistoNFTSlot
        from models.slot_calendario import SlotCalendario
        result = await db.execute(
            select(AcquistoNFT).where(AcquistoNFT.stripe_payment_id == pi_id_from_charge)
        )
        acquisto = result.scalar_one_or_none()
        if acquisto and acquisto.stato in ("pagato", "mintato"):
            acquisto.stato = "rimborsato"
            # Libera le ore acquistate — unica query JOIN per evitare N+1
            links_res = await db.execute(
                select(AcquistoNFTSlot, SlotCalendario)
                .join(SlotCalendario, AcquistoNFTSlot.slot_calendario_id == SlotCalendario.id)
                .where(AcquistoNFTSlot.acquisto_nft_id == acquisto.id)
                .with_for_update()
            )
            for ln, slot in links_res.all():
                ore_da_liberare = set(ln.ore_acquistate or [])
                slot.ore_vendute = sorted(set(slot.ore_vendute or []) - ore_da_liberare)
                slot.ore_in_lock = []
                slot.bloccato_fino_a = None
                h_inizio = slot.ora_inizio.hour
                ore_fascia = set(range(h_inizio, h_inizio + slot.ore_totali))
                slot.stato = (
                    "esaurito" if set(slot.ore_vendute) >= ore_fascia
                    else "parziale" if slot.ore_vendute
                    else "libero"
                )
            await db.flush()

    log.processed = True
    log.processed_at = datetime.now(timezone.utc)
    await db.flush()

    # Commit ESPLICITO prima di accodare il mint: evita l'enqueue-before-commit
    # (il worker non deve mai vedere uno stato non committato o poi rolled-back).
    await db.commit()
    if acq_to_mint is not None:
        from tasks.mint import esegui_mint_task
        esegui_mint_task.delay(str(acq_to_mint))

    return {"status": "ok"}
