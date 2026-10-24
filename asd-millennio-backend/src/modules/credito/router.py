from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import RequireDirigenza, get_current_user
from models.socio import Socio
from modules.credito.service import CreditoService
from schemas.credito import (
    MioCreditoResponse,
    MovimentoDirigenzaCreate,
    RicaricaOnlineRequest,
    RicaricaOnlineResponse,
    RiepilogoCreditoResponse,
    SaldoSocioResponse,
    SchedaCreditoSocioResponse,
)

router = APIRouter(prefix="/credito", tags=["Credito interno"])
dirigenza_router = APIRouter(prefix="/dirigenza/credito", tags=["Dirigenza — Credito interno"])


async def _socio_corrente(user: dict, db: AsyncSession) -> Socio:
    socio = (
        await db.execute(select(Socio).where(Socio.keycloak_user_id == user["sub"]))
    ).scalar_one_or_none()
    if not socio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo non trovato")
    return socio


# ─── Socio ──────────────────────────────────────────────────────────────────

@router.get("/me", response_model=MioCreditoResponse)
async def mio_credito(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    return await CreditoService(db).mio(await _socio_corrente(user, db))


@router.post("/ricarica", response_model=RicaricaOnlineResponse)
async def ricarica_online(
    data: RicaricaOnlineRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Avvia una ricarica con Stripe Checkout (solo se attivata in configurazione)."""
    url = await CreditoService(db).avvia_ricarica(await _socio_corrente(user, db), data.importo_eur)
    return RicaricaOnlineResponse(stripe_checkout_url=url)


# ─── Dirigenza ──────────────────────────────────────────────────────────────

@dirigenza_router.get("/riepilogo", response_model=RiepilogoCreditoResponse)
async def riepilogo(_=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")):
    return await CreditoService(db).riepilogo()


@dirigenza_router.get("/soci", response_model=list[SaldoSocioResponse])
async def cerca_soci(
    q: str = Query(..., min_length=2, max_length=60), _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")
):
    return await CreditoService(db).cerca(q)


@dirigenza_router.get("/soci/{socio_id}", response_model=SchedaCreditoSocioResponse)
async def scheda_socio(socio_id: UUID, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")):
    return await CreditoService(db).scheda(socio_id)


@dirigenza_router.post("/soci/{socio_id}/movimenti", response_model=SchedaCreditoSocioResponse, status_code=201)
async def registra_movimento(
    socio_id: UUID,
    data: MovimentoDirigenzaCreate,
    user: dict = RequireDirigenza,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Accredito, storno (correzione) o ricarica in sede. Il registro non si modifica: si aggiungono movimenti."""
    operatore_id = (
        await db.execute(select(Socio.id).where(Socio.keycloak_user_id == user["sub"]))
    ).scalar_one_or_none()
    return await CreditoService(db).registra_dirigenza(socio_id, data, operatore_id)
