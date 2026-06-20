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
    CheckoutCampoResponse,
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
    """Lista giorni disponibili con campi liberi nell'intervallo richiesto."""
    svc = CampiService(db)
    return await svc.lista_disponibilita(data_inizio, data_fine)


@router.post("/prenota", response_model=CheckoutCampoResponse)
async def prenota_campo(
    body: PrenotazioneCampoCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Crea una prenotazione in stato 'bloccata' e restituisce l'URL Stripe Checkout.
    La prenotazione diventa 'confermata' solo dopo il pagamento (webhook Stripe).
    """
    socio_id = await _get_socio_id(user, db)
    svc = CampiService(db)
    return await svc.avvia_prenotazione(
        socio_id=socio_id,
        template_id=body.template_id,
        data=body.data,
    )


@router.get("/le-mie-prenotazioni", response_model=List[PrenotazioneCampoResponse])
async def le_mie_prenotazioni(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    socio_id = await _get_socio_id(user, db)
    svc = CampiService(db)
    return await svc.lista_prenotazioni_socio(socio_id)


@router.delete("/prenota/{prenotazione_id}", response_model=CancellazioneCampoResponse)
async def cancella_prenotazione(
    prenotazione_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    socio_id = await _get_socio_id(user, db)
    svc = CampiService(db)
    pren = await svc.cancella_prenotazione(socio_id, prenotazione_id)
    return CancellazioneCampoResponse(
        prenotazione_id=pren.id,
        messaggio="Prenotazione cancellata con successo",
    )
