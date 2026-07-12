from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.socio import Socio
from modules.campi.service import CampiService
from schemas.campi import (
    CancellazioneCampoResponse,
    CheckoutCarrelloResponse,
    GiornoDisponibileResponse,
    PrenotazioneCampoCreate,
    PrenotazioneCampoResponse,
)

router = APIRouter(prefix="/campi", tags=["M02 — Campi"])


async def _get_socio_id(user: dict, db: AsyncSession) -> UUID:
    r = await db.execute(select(Socio).where(Socio.keycloak_user_id == user["sub"]))
    socio = r.scalar_one_or_none()
    if not socio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo socio non trovato")
    return socio.id


@router.get("/disponibilita", response_model=List[GiornoDisponibileResponse])
async def disponibilita_campi(
    data_inizio: date = Query(...),
    data_fine: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Slot da 1 ora prenotabili nell'intervallo, con i campi liberi per ogni ora."""
    return await CampiService(db).lista_disponibilita(data_inizio, data_fine)


# ─── Carrello (più ore, un unico pagamento) ─────────────────────────────────

@router.post("/carrello", response_model=PrenotazioneCampoResponse)
async def aggiungi_al_carrello(
    body: PrenotazioneCampoCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Blocca un'ora (30 min) e la aggiunge al carrello — nessun pagamento ancora."""
    socio_id = await _get_socio_id(user, db)
    return await CampiService(db).aggiungi_al_carrello(
        socio_id=socio_id,
        template_id=body.template_id,
        data=body.data,
        ora_inizio=body.ora_inizio,
    )


@router.get("/carrello", response_model=List[PrenotazioneCampoResponse])
async def lista_carrello(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Ore bloccate non ancora pagate (carrello). I lock scaduti vengono rilasciati."""
    socio_id = await _get_socio_id(user, db)
    return await CampiService(db).lista_carrello(socio_id)


@router.post("/carrello/checkout", response_model=CheckoutCarrelloResponse)
async def checkout_carrello(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Crea un unico Stripe Checkout per tutte le ore nel carrello."""
    socio_id = await _get_socio_id(user, db)
    return await CampiService(db).checkout_carrello(socio_id)


# ─── Prenotazioni confermate ─────────────────────────────────────────────────

@router.get("/le-mie-prenotazioni", response_model=List[PrenotazioneCampoResponse])
async def le_mie_prenotazioni(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    socio_id = await _get_socio_id(user, db)
    return await CampiService(db).lista_prenotazioni_socio(socio_id)


@router.delete("/prenota/{prenotazione_id}", response_model=CancellazioneCampoResponse)
async def cancella_prenotazione(
    prenotazione_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Rimuove un'ora dal carrello (se bloccata) o cancella una prenotazione confermata."""
    socio_id = await _get_socio_id(user, db)
    pren = await CampiService(db).cancella_prenotazione(socio_id, prenotazione_id)
    return CancellazioneCampoResponse(
        prenotazione_id=pren.id,
        messaggio="Prenotazione rimossa",
    )
