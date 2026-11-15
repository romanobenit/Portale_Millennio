from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import RequireDirigenza, RequireTracker
from models.tracker import MembroTracker
from modules.tracker.service import TrackerService
from schemas.tracker import (
    CancellaPersiRequest,
    CancellaPersiResponse,
    ContattoCreate,
    ContattoDettaglioResponse,
    ContattoResponse,
    ContattoUpdate,
    CostoIstruttoreCreate,
    CostoIstruttoreResponse,
    Fonte,
    ListaContattiResponse,
    MembroResponse,
    MeTrackerResponse,
    RiepilogoResponse,
    Sport,
    Stato,
)

router = APIRouter(prefix="/tracker", tags=["Tracker iscritti"])


async def membro(user: dict = RequireTracker, db: AsyncSession = Depends(get_db, scope="function")) -> MembroTracker:
    return (await TrackerService(db).membro_corrente(user))[0]


# ─── Rita e dirigenza ───────────────────────────────────────────────────────

@router.get("/me", response_model=MeTrackerResponse)
async def me(user: dict = RequireTracker, db: AsyncSession = Depends(get_db, scope="function")):
    m, dirigenza = await TrackerService(db).membro_corrente(user)
    return MeTrackerResponse(id=m.id, nome=m.nome, ruolo=m.ruolo, dirigenza=dirigenza)


@router.get("/membri", response_model=list[MembroResponse])
async def membri(_: MembroTracker = Depends(membro), db: AsyncSession = Depends(get_db, scope="function")):
    """Possibili responsabili del follow-up: chi ha già usato il tracker."""
    return await TrackerService(db).membri()


@router.get("/contatti", response_model=ListaContattiResponse)
async def lista_contatti(
    q: str | None = Query(None, max_length=60),
    sport: Sport | None = None,
    fonte: Fonte | None = None,
    stato: Stato | None = None,
    responsabile_id: UUID | None = None,
    test: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    _: MembroTracker = Depends(membro),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await TrackerService(db).lista(
        q=q, sport=sport, fonte=fonte, stato=stato, responsabile_id=responsabile_id,
        test=test, page=page, limit=limit,
    )


@router.get("/contatti/doppioni", response_model=list[ContattoResponse])
async def possibili_doppioni(
    nome: str = Query(..., min_length=2, max_length=120),
    escludi_id: UUID | None = None,
    _: MembroTracker = Depends(membro),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await TrackerService(db).possibili_doppioni(nome, escludi_id)


@router.post("/contatti", response_model=ContattoResponse, status_code=201)
async def crea_contatto(
    data: ContattoCreate, m: MembroTracker = Depends(membro), db: AsyncSession = Depends(get_db, scope="function")
):
    return await TrackerService(db).crea(data, m)


@router.get("/contatti/{contatto_id}", response_model=ContattoDettaglioResponse)
async def dettaglio_contatto(
    contatto_id: UUID, _: MembroTracker = Depends(membro), db: AsyncSession = Depends(get_db, scope="function")
):
    return await TrackerService(db).dettaglio(contatto_id)


@router.patch("/contatti/{contatto_id}", response_model=ContattoResponse)
async def aggiorna_contatto(
    contatto_id: UUID,
    data: ContattoUpdate,
    m: MembroTracker = Depends(membro),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await TrackerService(db).aggiorna(contatto_id, data, m)


@router.get("/follow-up", response_model=list[ContattoResponse])
async def miei_followup(m: MembroTracker = Depends(membro), db: AsyncSession = Depends(get_db, scope="function")):
    return await TrackerService(db).miei_followup(m)


# ─── Solo dirigenza ─────────────────────────────────────────────────────────

@router.delete("/contatti/{contatto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancella_su_richiesta(
    contatto_id: UUID, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")
):
    """Solo se l'interessato chiede di essere rimosso: negli altri casi lo stato diventa "perso"."""
    await TrackerService(db).cancella_su_richiesta(contatto_id)


@router.post("/persi/cancella", response_model=CancellaPersiResponse)
async def cancella_persi(
    data: CancellaPersiRequest, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")
):
    """Pulizia manuale dei contatti "perso": con `conferma=false` dice solo quanti sono."""
    return await TrackerService(db).cancella_persi(data.fino_al, data.conferma)


@router.get("/riepilogo", response_model=RiepilogoResponse)
async def riepilogo(
    fonte: Fonte | None = None,
    dal: date | None = None,
    al: date | None = None,
    test: bool = False,
    _=RequireDirigenza,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    if dal and al and al < dal:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Intervallo di date non valido")
    return await TrackerService(db).riepilogo(fonte=fonte, dal=dal, al=al, solo_test=test)


@router.get("/costi-istruttore", response_model=list[CostoIstruttoreResponse])
async def costi(_=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")):
    return await TrackerService(db).costi()


@router.post("/costi-istruttore", response_model=CostoIstruttoreResponse, status_code=201)
async def imposta_costo(
    data: CostoIstruttoreCreate, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")
):
    return await TrackerService(db).imposta_costo(data)


@router.delete("/costi-istruttore/{costo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def elimina_costo(costo_id: UUID, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")):
    await TrackerService(db).elimina_costo(costo_id)
