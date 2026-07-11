"""
Assemblaggio dei dati e generazione del certificato PDF a partire dal DB.

Condiviso dal worker di mint (invio automatico post-conio) e dall'endpoint di
download on-demand della pagina "I miei NFT", così la logica non è duplicata.
"""
import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.acquisto_nft import AcquistoNFT, AcquistoNFTSlot
from models.slot_calendario import SlotCalendario
from models.socio import Socio
from models.tessera import Tessera
from modules.nft.certificato import genera_certificato_pdf

settings = get_settings()


def polygonscan_base() -> str:
    """Base URL Polygonscan in funzione della chain configurata (mainnet vs Amoy)."""
    return "https://polygonscan.com" if settings.polygon_chain_id == 137 else "https://amoy.polygonscan.com"


def polygonscan_token_url(contract_address: str, token_id: int) -> str:
    return f"{polygonscan_base()}/token/{contract_address}?a={token_id}"


async def _raccogli_ore(db: AsyncSession, acquisto_id: UUID) -> list[dict]:
    links = (await db.execute(
        select(AcquistoNFTSlot).where(AcquistoNFTSlot.acquisto_nft_id == acquisto_id)
    )).scalars().all()
    slot_ids = [ln.slot_calendario_id for ln in links]
    slots = {
        s.id: s for s in (await db.execute(
            select(SlotCalendario).where(SlotCalendario.id.in_(slot_ids))
        )).scalars().all()
    }
    ore: list[dict] = []
    for ln in links:
        s = slots.get(ln.slot_calendario_id)
        if not s:
            continue
        for ora in (ln.ore_acquistate or []):
            ore.append({"data": s.data, "fascia": s.fascia, "ora": int(ora)})
    ore.sort(key=lambda o: (o["data"], o["ora"]))
    return ore


async def genera_pdf_certificato(db: AsyncSession, acquisto_id: UUID) -> bytes:
    """
    Ricarica l'acquisto (fresco) e genera il PDF. Solleva ValueError se l'acquisto
    non è mintato. Rilegge tutto dal DB per essere sicuro anche subito dopo un commit.
    """
    acquisto = (await db.execute(
        select(AcquistoNFT).where(AcquistoNFT.id == acquisto_id)
    )).scalar_one_or_none()
    if acquisto is None:
        raise ValueError(f"Acquisto {acquisto_id} non trovato")
    if acquisto.stato != "mintato" or acquisto.token_id is None:
        raise ValueError(f"Acquisto {acquisto_id} non ancora mintato: certificato non disponibile")

    socio = (await db.execute(
        select(Socio).where(Socio.id == acquisto.socio_id)
    )).scalar_one()
    sos = (await db.execute(
        select(Tessera).where(
            Tessera.socio_id == acquisto.socio_id,
            Tessera.sport == "sostenitore",
            Tessera.stato == "attiva",
        ).order_by(Tessera.numero_tessera.desc())
    )).scalars().first()

    ore = await _raccogli_ore(db, acquisto_id)

    # genera_certificato_pdf è CPU-bound (reportlab) → thread separato
    return await asyncio.to_thread(
        genera_certificato_pdf,
        nome=socio.nome,
        cognome=socio.cognome,
        tessera_sostenitore=sos.numero_tessera if sos else None,
        token_id=acquisto.token_id,
        contract_address=acquisto.contract_address or settings.contract_address_palasirio_nft,
        wallet_address=acquisto.wallet_address or "",
        mint_tx_hash=acquisto.mint_tx_hash,
        ipfs_uri=acquisto.ipfs_uri or "",
        ore=ore,
        importo_eur=float(acquisto.importo_eur),
        data_emissione=datetime.now(timezone.utc).date(),
        polygonscan_base=polygonscan_base(),
    )
