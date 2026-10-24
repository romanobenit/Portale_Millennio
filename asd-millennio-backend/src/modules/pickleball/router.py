from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import RequireStaff, get_current_user
from models.socio import Socio
from modules.pickleball.service import PickleballService
from schemas.pickleball import (
    ContestaRequest,
    DashboardPickleballDirigenza,
    Formato,
    GiocatoreRicerca,
    MioPickleballResponse,
    PartitaCreate,
    PartitaDirigenzaCreate,
    PartitaResponse,
    ProfiloAtletaResponse,
    ProfiloAtletaUpdate,
    RigaClassifica,
)

router = APIRouter(prefix="/pickleball", tags=["Pickleball — Classifica"])
dirigenza_router = APIRouter(prefix="/dirigenza/pickleball", tags=["Dirigenza — Pickleball"])


async def _socio_corrente(user: dict, db: AsyncSession) -> Socio:
    socio = (
        await db.execute(select(Socio).where(Socio.keycloak_user_id == user["sub"]))
    ).scalar_one_or_none()
    if not socio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo non trovato")
    return socio


# ─── Socio ──────────────────────────────────────────────────────────────────

@router.get("/classifica", response_model=list[RigaClassifica])
async def classifica(
    formato: Formato = Query("doppio"),
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Classifica Elo del club (soci autenticati). Esclusi minori e chi ha scelto di non comparire."""
    return await PickleballService(db).classifica(formato)


@router.get("/me", response_model=MioPickleballResponse)
async def mio(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    return await PickleballService(db).mio(await _socio_corrente(user, db))


@router.put("/me/profilo", response_model=ProfiloAtletaResponse)
async def aggiorna_profilo(
    data: ProfiloAtletaUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await PickleballService(db).aggiorna_profilo(await _socio_corrente(user, db), data)


@router.get("/giocatori", response_model=list[GiocatoreRicerca])
async def cerca_giocatori(
    q: str = Query(..., min_length=2, max_length=60),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    socio = await _socio_corrente(user, db)
    return await PickleballService(db).cerca_giocatori(q, escludi=socio.id)


@router.post("/partite", response_model=PartitaResponse, status_code=201)
async def registra_partita(
    data: PartitaCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Il socio registra una partita: conta in classifica solo dopo la conferma di un avversario."""
    return await PickleballService(db).registra_socio(await _socio_corrente(user, db), data)


@router.post("/partite/{partita_id}/conferma", status_code=204)
async def conferma_partita(
    partita_id: UUID, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")
):
    await PickleballService(db).conferma(await _socio_corrente(user, db), partita_id)


@router.post("/partite/{partita_id}/contesta", status_code=204)
async def contesta_partita(
    partita_id: UUID,
    data: ContestaRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    await PickleballService(db).contesta(await _socio_corrente(user, db), partita_id, data.motivo)


@router.delete("/partite/{partita_id}", status_code=204)
async def ritira_partita(
    partita_id: UUID, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")
):
    await PickleballService(db).ritira(await _socio_corrente(user, db), partita_id)


# ─── Dirigenza / staff ──────────────────────────────────────────────────────

async def _operatore_id(user: dict, db: AsyncSession) -> UUID | None:
    return (
        await db.execute(select(Socio.id).where(Socio.keycloak_user_id == user["sub"]))
    ).scalar_one_or_none()


@dirigenza_router.get("/dashboard", response_model=DashboardPickleballDirigenza)
async def dashboard(_=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    return await PickleballService(db).dashboard_dirigenza()


@dirigenza_router.get("/classifica", response_model=list[RigaClassifica])
async def classifica_completa(
    formato: Formato = Query("doppio"), _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    """Classifica completa con nomi per esteso (inclusi minori e profili nascosti)."""
    return await PickleballService(db).classifica(formato, completa=True)


@dirigenza_router.get("/partite", response_model=list[PartitaResponse])
async def lista_partite(
    stato: Literal["in_attesa_conferma", "confermata", "contestata", "annullata"] | None = None,
    _=RequireStaff,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await PickleballService(db).lista_dirigenza(stato)


@dirigenza_router.get("/giocatori", response_model=list[GiocatoreRicerca])
async def cerca_giocatori_dirigenza(
    q: str = Query(..., min_length=2, max_length=60), _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    return await PickleballService(db).cerca_giocatori_dirigenza(q)


@dirigenza_router.post("/partite", response_model=PartitaResponse, status_code=201)
async def registra_partita_dirigenza(
    data: PartitaDirigenzaCreate, user: dict = RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    """Risultato inserito dalla dirigenza (es. torneo): confermato subito e conteggiato in classifica."""
    return await PickleballService(db).registra_dirigenza(await _operatore_id(user, db), data)


@dirigenza_router.post("/partite/{partita_id}/{esito}", status_code=204)
async def risolvi_partita(
    partita_id: UUID,
    esito: Literal["conferma", "annulla"],
    user: dict = RequireStaff,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Conferma una partita in attesa o contestata, oppure la annulla (anche se già confermata)."""
    await PickleballService(db).risolvi(partita_id, esito, await _operatore_id(user, db))
