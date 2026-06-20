from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limit import limiter
from core.security import get_current_user
from modules.calendario.service import CalendarioService
from schemas.calendario import DisponibilitaFascia, LockRequest, RiepilogoSelezione, SlotResponse

router = APIRouter(prefix="/calendario", tags=["M02 — Calendario"])


@router.get("", response_model=list[SlotResponse])
@limiter.limit("60/minute")
async def lista_slot(
    request: Request,
    data_inizio: date | None = Query(None),
    data_fine: date | None = Query(None),
    fascia: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await CalendarioService(db).lista_slot(data_inizio, data_fine, fascia, page, limit)


@router.get("/disponibilita", response_model=list[DisponibilitaFascia])
@limiter.limit("60/minute")
async def disponibilita(
    request: Request,
    data_inizio: date = Query(default_factory=date.today),
    data_fine: date = Query(default_factory=lambda: date.today() + timedelta(days=90)),
    db: AsyncSession = Depends(get_db),
):
    """Ore libere con prezzo dinamico per ogni fascia. Chiamata ad ogni apertura del calendario."""
    return await CalendarioService(db).disponibilita(data_inizio, data_fine)


@router.post("/lock", response_model=RiepilogoSelezione, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def lock_selezione(
    request: Request,
    payload: LockRequest,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Blocca le ore selezionate per 30 minuti e restituisce il prezzo dinamico.
    Raise 409 se un'ora è già venduta o in lock da altro acquirente.
    """
    async with db.begin():
        riepilogo = await CalendarioService(db).lock_selezione(payload)
    return riepilogo


@router.get("/riepilogo-selezione", response_model=RiepilogoSelezione)
@limiter.limit("30/minute")
async def riepilogo_selezione(
    request: Request,
    slot_id: list[UUID] = Query(...),
    ore: list[int] = Query(...),
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calcolo prezzo senza lock (anteprima). Usa lock per il flusso reale di acquisto."""
    from schemas.calendario import OreSelezione
    from modules.calendario.service import CalendarioService

    svc = CalendarioService(db)
    slots_data = []
    for sid in slot_id:
        slot = await svc.get_slot(sid)
        slots_data.append({"slot": slot, "ore": ore})
    return await svc.calcola_prezzo(slots_data)


@router.get("/{slot_id}", response_model=SlotResponse)
@limiter.limit("120/minute")
async def get_slot(
    request: Request,
    slot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    slot = await CalendarioService(db).get_slot(slot_id)
    return SlotResponse.model_validate(slot)
