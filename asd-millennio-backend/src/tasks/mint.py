"""
Task Celery per il mint NFT Palasirion.

Flusso:
  conferma_pagamento() → esegui_mint_task.delay(acquisto_id)
    → _run_mint() [async]
      → iCal → IPFS → mint on-chain → DB commit
    → in caso di errore: retry (max 3, backoff esponenziale 30/60/120s)
    → dopo max retry: _segna_fallito() rilascia gli slot e marca l'acquisto come fallito
"""
import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

import stripe
from celery.utils.log import get_task_logger
from sqlalchemy import select

from core.celery_app import celery_app
from core.config import get_settings
from core.database import AsyncSessionLocal
from models.acquisto_nft import AcquistoNFT, AcquistoNFTSlot
from models.slot_calendario import SlotCalendario
from models.tessera import Tessera
from models.wallet import WalletCustodiale
from modules.calendario.service import CalendarioService
from modules.nft.ical import calcola_sha256, genera_ical_content
from modules.nft.ipfs import costruisci_metadati_nft, upload_json_to_ipfs

task_logger = get_task_logger(__name__)
settings = get_settings()
stripe.api_key = settings.stripe_secret_key


async def _run_mint(acquisto_id: UUID) -> None:
    """Core async: genera iCal, carica IPFS, minta NFT, aggiorna DB."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(AcquistoNFT).where(AcquistoNFT.id == acquisto_id))
            acquisto = result.scalar_one()

            if acquisto.stato == "mintato":
                task_logger.info("Acquisto %s già mintato — skip.", acquisto_id)
                return

            links_result = await db.execute(
                select(AcquistoNFTSlot).where(AcquistoNFTSlot.acquisto_nft_id == acquisto_id)
            )
            links = list(links_result.scalars().all())
            slot_ids = [ln.slot_calendario_id for ln in links]
            # ore_per_slot ricavato dagli stessi link — nessuna seconda query
            ore_per_slot: dict[str, list[int]] = {
                str(ln.slot_calendario_id): list(ln.ore_acquistate or [])
                for ln in links
            }
            ore_totali = sum(len(ore) for ore in ore_per_slot.values())

            slots_result = await db.execute(
                select(SlotCalendario).where(SlotCalendario.id.in_(slot_ids))
            )
            slots = list(slots_result.scalars().all())

            tessera_result = await db.execute(
                select(Tessera).where(
                    Tessera.socio_id == acquisto.socio_id,
                    Tessera.stato == "attiva",
                )
            )
            tessera = tessera_result.scalars().first()
            tessera_id = tessera.numero_tessera if tessera else str(acquisto.socio_id)

            wallet_result = await db.execute(
                select(WalletCustodiale).where(WalletCustodiale.socio_id == acquisto.socio_id)
            )
            wallet = wallet_result.scalar_one()

            data_primo = min(s.data for s in slots).isoformat() if slots else ""
            fascia_conti: dict[str, int] = {"notte": 0, "mattina": 0, "pomeriggio": 0}
            for s in slots:
                fascia_conti[s.fascia] += 1
            fascia_prevalente = max(fascia_conti, key=fascia_conti.get) if slots else "notte"

            from modules.nft.blockchain import mint_nft_with_slots, update_token_uri

            # CHECKPOINT idempotenza: minta on-chain SOLO se non già fatto.
            # Se un tentativo precedente ha mintato ma è poi fallito (update_token_uri,
            # IPFS, commit), token_id è già persistito → si riprende senza ri-mintare.
            if acquisto.token_id is None:
                ical_pre = genera_ical_content(
                    slots, 0, tessera_id, settings.contract_address_palasirion_nft,
                    ore_per_slot=ore_per_slot,
                )
                ical_hash_pre = calcola_sha256(ical_pre)
                metadati_pre = costruisci_metadati_nft(
                    slots_count=len(slots),
                    data_primo_slot=data_primo,
                    fascia_prevalente=fascia_prevalente,
                    ore_totali=ore_totali,
                    importo_eur=float(acquisto.importo_eur),
                    ical_content=ical_pre,
                    ical_sha256=ical_hash_pre,
                    tessera_id=tessera_id,
                )
                ipfs_uri_temp = await upload_json_to_ipfs(metadati_pre)

                # slotKey per-ora "{data}_{fascia}_{ora}" → registrati on-chain:
                # il contratto reverta se una qualsiasi ora è già prenotata (anti double-sell).
                slot_keys = [
                    f"{slot.data.isoformat()}_{slot.fascia}_{ora:02d}"
                    for slot in slots
                    for ora in sorted(ore_per_slot.get(str(slot.id), []))
                ]
                token_id = await mint_nft_with_slots(
                    wallet.wallet_address, ipfs_uri_temp, slot_keys, ical_hash_pre,
                )
                # Persisti SUBITO il token_id in un commit dedicato: rende il mint
                # idempotente rispetto ai retry (niente doppio mint on-chain).
                acquisto.token_id = token_id
                acquisto.contract_address = settings.contract_address_palasirion_nft
                await db.commit()
            else:
                token_id = acquisto.token_id
                task_logger.info(
                    "Acquisto %s già mintato on-chain (token_id=%s) — riprendo dal checkpoint.",
                    acquisto_id, token_id,
                )

            # Rigenera iCal/metadati con il token_id reale → IPFS → aggiorna URI on-chain.
            # update_token_uri è ri-eseguibile (idempotente a livello di stato finale).
            ical_content = genera_ical_content(
                slots, token_id, tessera_id, settings.contract_address_palasirion_nft,
                ore_per_slot=ore_per_slot,
            )
            ical_hash = calcola_sha256(ical_content)

            metadati = costruisci_metadati_nft(
                slots_count=len(slots),
                data_primo_slot=data_primo,
                fascia_prevalente=fascia_prevalente,
                ore_totali=ore_totali,
                importo_eur=float(acquisto.importo_eur),
                ical_content=ical_content,
                ical_sha256=ical_hash,
                tessera_id=tessera_id,
            )
            ipfs_uri = await upload_json_to_ipfs(metadati)
            await update_token_uri(token_id, ipfs_uri, ical_hash)

            acquisto.stato = "mintato"
            acquisto.ipfs_uri = ipfs_uri
            # Backup off-chain (PRD §RNF-BLOCKCHAIN-002)
            acquisto.metadati_json = json.dumps(metadati)
            acquisto.ical_content = ical_content
            acquisto.ical_sha256 = ical_hash

            # Le ore sono già state marcate come vendute alla CONFERMA del pagamento
            # (claim atomico FOR UPDATE in conferma_pagamento). Qui marchiamo solo
            # il token_id sugli slot per riferimento.
            for slot in slots:
                slot.nft_token_id = token_id

            await db.commit()
            task_logger.info(
                "NFT mintato con successo: acquisto=%s token_id=%s", acquisto_id, token_id
            )

        except Exception:
            await db.rollback()
            raise


async def _segna_fallito(acquisto_id: UUID) -> None:
    """
    Mint fallito definitivamente dopo i retry.
    Rimborsa il socio (idempotente), rilascia le ore claimate alla conferma del
    pagamento e libera gli slot così possono essere rivenduti.
    """
    async with AsyncSessionLocal() as db:
        try:
            acquisto = (await db.execute(
                select(AcquistoNFT).where(AcquistoNFT.id == acquisto_id)
            )).scalar_one_or_none()
            if not acquisto:
                task_logger.error("Acquisto non trovato per segna_fallito: %s", acquisto_id)
                return

            # Rimborso Stripe idempotente (il pagamento è già stato incassato)
            refunded = False
            if acquisto.stripe_payment_id:
                try:
                    await asyncio.to_thread(
                        stripe.Refund.create,
                        payment_intent=acquisto.stripe_payment_id,
                        idempotency_key=f"refund-{acquisto_id}",
                    )
                    refunded = True
                except Exception as refund_err:  # noqa: BLE001
                    task_logger.critical(
                        "RIMBORSO FALLITO per acquisto %s: %s — intervento manuale richiesto",
                        acquisto_id, refund_err,
                    )
            acquisto.stato = "rimborsato" if refunded else "fallito"

            # Rilascia le ore claimate alla conferma (rimuovi ore_acquistate da ore_vendute)
            links_join = await db.execute(
                select(AcquistoNFTSlot, SlotCalendario)
                .join(SlotCalendario, AcquistoNFTSlot.slot_calendario_id == SlotCalendario.id)
                .where(AcquistoNFTSlot.acquisto_nft_id == acquisto_id)
                .with_for_update()
            )
            n_slot = 0
            for ln, slot in links_join.all():
                n_slot += 1
                ore_acq = set(ln.ore_acquistate or [])
                slot.ore_vendute = sorted(set(slot.ore_vendute or []) - ore_acq)
                slot.ore_in_lock = sorted(set(slot.ore_in_lock or []) - ore_acq)
                slot.nft_token_id = None
                if not slot.ore_in_lock:
                    slot.bloccato_fino_a = None
                slot.stato = CalendarioService._calcola_stato(slot)

            await db.commit()
            task_logger.error(
                "Acquisto %s %s. %d slot rilasciati.",
                acquisto_id,
                "RIMBORSATO" if refunded else "FALLITO (rimborso manuale necessario)",
                n_slot,
            )
            # TODO: notifica email al socio via Resend (Sprint 2)

        except Exception as cleanup_exc:
            await db.rollback()
            task_logger.critical(
                "Errore critico nel cleanup di acquisto %s: %s — intervento manuale richiesto.",
                acquisto_id,
                cleanup_exc,
            )


@celery_app.task(
    bind=True,
    max_retries=3,
    name="tasks.mint.esegui_mint_task",
)
def esegui_mint_task(self, acquisto_id_str: str) -> None:
    """
    Celery task: genera iCal, carica IPFS, minta NFT su Polygon.
    Retry automatico (max 3) con backoff esponenziale: 30s → 60s → 120s.
    Alla terza fallita definitiva: marca acquisto come 'fallito' e rilascia gli slot.
    """
    acquisto_id = UUID(acquisto_id_str)
    try:
        asyncio.run(_run_mint(acquisto_id))
    except Exception as exc:
        countdown = 30 * (2 ** self.request.retries)  # 30s, 60s, 120s
        task_logger.warning(
            "Mint fallito per acquisto %s (tentativo %d/%d). Retry tra %ds: %s",
            acquisto_id_str,
            self.request.retries + 1,
            self.max_retries + 1,
            countdown,
            exc,
        )
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            task_logger.error(
                "Mint definitivamente fallito per acquisto %s dopo %d tentativi.",
                acquisto_id_str,
                self.max_retries + 1,
            )
            asyncio.run(_segna_fallito(acquisto_id))
            raise
