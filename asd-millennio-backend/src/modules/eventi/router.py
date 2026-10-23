from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import RequireDirigenza, RequireStaff, get_current_user
from models.socio import Socio
from modules.eventi.service import EventiService
from schemas.eventi import (
    AggiungiPartecipanteRequest,
    EventoCreate,
    EventoDettaglioResponse,
    EventoDirigenzaResponse,
    EventoPubblicoResponse,
    EventoUpdate,
    MieiEventiResponse,
    PresenzeManualiUpdate,
    PrenotaEventoRequest,
    PrenotaEventoResponse,
    PrenotazioneEventoResponse,
    SegnaPresenzaRequest,
    SocioRicercaResponse,
)

router = APIRouter(prefix="/eventi", tags=["M02 — Eventi campo"])
dirigenza_router = APIRouter(prefix="/dirigenza/eventi", tags=["Dirigenza — Eventi campo"])


async def _socio_corrente(user: dict, db: AsyncSession) -> Socio:
    socio = (
        await db.execute(select(Socio).where(Socio.keycloak_user_id == user["sub"]))
    ).scalar_one_or_none()
    if not socio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo non trovato")
    return socio


# ─── Pubblico / socio ───────────────────────────────────────────────────────

@router.get("", response_model=list[EventoPubblicoResponse])
async def prossimi_eventi(db: AsyncSession = Depends(get_db, scope="function")):
    """Pubblico: eventi programmati non ancora conclusi, dal più vicino."""
    return await EventiService(db).lista_pubblica()


@router.get("/mie", response_model=MieiEventiResponse)
async def miei_eventi(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    return await EventiService(db).miei_eventi(await _socio_corrente(user, db))


@router.post("/{evento_id}/prenota", response_model=PrenotaEventoResponse, status_code=201)
async def prenota_evento(
    evento_id: UUID,
    data: PrenotaEventoRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    socio = await _socio_corrente(user, db)
    return await EventiService(db).prenota(socio, evento_id, data.modalita)


@router.post("/prenotazioni/{prenotazione_id}/annulla", response_model=PrenotazioneEventoResponse)
async def annulla_prenotazione(
    prenotazione_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    socio = await _socio_corrente(user, db)
    return await EventiService(db).annulla(socio.id, prenotazione_id)


@router.post("/{evento_id}/lista-attesa", status_code=status.HTTP_204_NO_CONTENT)
async def iscrivi_lista_attesa(
    evento_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    socio = await _socio_corrente(user, db)
    await EventiService(db).iscrivi_lista_attesa(socio.id, evento_id)


@router.delete("/{evento_id}/lista-attesa", status_code=status.HTTP_204_NO_CONTENT)
async def esci_lista_attesa(
    evento_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    socio = await _socio_corrente(user, db)
    await EventiService(db).esci_lista_attesa(socio.id, evento_id)


# ─── Dirigenza / staff ──────────────────────────────────────────────────────

@dirigenza_router.get("", response_model=list[EventoDirigenzaResponse])
async def lista_eventi(
    data_inizio: date = Query(...),
    data_fine: date = Query(...),
    _=RequireStaff,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    if data_fine < data_inizio:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Intervallo di date non valido")
    return await EventiService(db).lista_dirigenza(data_inizio, data_fine)


@dirigenza_router.post("", response_model=EventoDirigenzaResponse, status_code=201)
async def crea_evento(data: EventoCreate, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")):
    return await EventiService(db).crea_evento(data)


@dirigenza_router.get("/soci", response_model=list[SocioRicercaResponse])
async def cerca_soci(
    q: str = Query(..., min_length=2, max_length=60),
    _=RequireStaff,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await EventiService(db).cerca_soci(q)


@dirigenza_router.post("/soci/{socio_id}/azzera-assenze", status_code=status.HTTP_204_NO_CONTENT)
async def azzera_assenze(socio_id: UUID, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")):
    await EventiService(db).azzera_assenze(socio_id)


@dirigenza_router.get("/{evento_id}", response_model=EventoDettaglioResponse)
async def dettaglio_evento(evento_id: UUID, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    return await EventiService(db).dettaglio(evento_id)


@dirigenza_router.put("/{evento_id}", response_model=EventoDirigenzaResponse)
async def aggiorna_evento(
    evento_id: UUID, data: EventoUpdate, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")
):
    return await EventiService(db).aggiorna_evento(evento_id, data)


@dirigenza_router.post("/{evento_id}/annulla", response_model=EventoDirigenzaResponse)
async def annulla_evento(evento_id: UUID, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")):
    return await EventiService(db).annulla_evento(evento_id)


@dirigenza_router.put("/{evento_id}/presenze-manuali", response_model=EventoDirigenzaResponse)
async def imposta_presenze_manuali(
    evento_id: UUID, data: PresenzeManualiUpdate, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    return await EventiService(db).imposta_presenze_manuali(evento_id, data.presenze_manuali)


@dirigenza_router.post("/{evento_id}/partecipanti", response_model=PrenotaEventoResponse, status_code=201)
async def aggiungi_partecipante(
    evento_id: UUID, data: AggiungiPartecipanteRequest, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    """Prenotazione "pago in sede" inserita dalla segreteria per un associato."""
    return await EventiService(db).aggiungi_partecipante(evento_id, data.socio_id)


@dirigenza_router.patch("/prenotazioni/{prenotazione_id}", response_model=PrenotazioneEventoResponse)
async def segna_prenotazione(
    prenotazione_id: UUID, data: SegnaPresenzaRequest, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    """Segna presenza/assenza e pagamento in sede."""
    return await EventiService(db).segna(prenotazione_id, data)
