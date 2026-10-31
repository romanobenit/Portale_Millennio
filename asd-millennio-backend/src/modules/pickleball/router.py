from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import RequireDirigenza, RequireStaff, get_current_user
from models.socio import Socio
from modules.pickleball.service import PickleballService
from modules.pickleball.tornei import TorneiService
from schemas.pickleball import (
    CircuitoResponse,
    CollegaOspiteRequest,
    ConfigPickleballSchema,
    ContestaRequest,
    DashboardPickleballDirigenza,
    Formato,
    GiocatoreRicerca,
    ImportRisultatiResponse,
    MioPickleballResponse,
    OspiteCreate,
    OspiteResponse,
    OspiteUpdate,
    PartitaCreate,
    PartitaDirigenzaCreate,
    PartitaResponse,
    PiazzamentoResponse,
    PiazzamentoUpdate,
    ProfiloAtletaResponse,
    ProfiloAtletaUpdate,
    RigaClassifica,
    TorneoCreate,
    TorneoDettaglioResponse,
    TorneoResponse,
    TorneoUpdate,
)

Sesso = Literal["M", "F"]
ANNO = r"^\d{4}-\d{4}$"

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
    sesso: Sesso | None = None,
    eta_min: int | None = Query(None, ge=1, le=99),
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Classifica Elo del club (soci autenticati). Esclusi minori, inattivi e chi ha scelto di non comparire."""
    return await PickleballService(db).classifica(formato, sesso=sesso, eta_min=eta_min)


@router.get("/circuito", response_model=CircuitoResponse)
async def circuito(
    anno: str | None = Query(None, pattern=ANNO),
    categoria: str | None = Query(None, max_length=20),
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Circuito tornei della stagione per categoria: somma dei migliori piazzamenti."""
    return await TorneiService(db).circuito(anno, categoria, completo=False)


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
    formato: Formato = Query("doppio"),
    sesso: Sesso | None = None,
    eta_min: int | None = Query(None, ge=1, le=99),
    _=RequireStaff,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Classifica completa con nomi per esteso (inclusi minori, profili nascosti e inattivi)."""
    return await PickleballService(db).classifica(formato, completa=True, sesso=sesso, eta_min=eta_min)


@dirigenza_router.get("/circuito", response_model=CircuitoResponse)
async def circuito_completo(
    anno: str | None = Query(None, pattern=ANNO),
    categoria: str | None = Query(None, max_length=20),
    _=RequireStaff,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await TorneiService(db).circuito(anno, categoria, completo=True)


@dirigenza_router.get("/config", response_model=ConfigPickleballSchema)
async def leggi_config(_=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    return await TorneiService(db).leggi_config()


@dirigenza_router.put("/config", response_model=ConfigPickleballSchema)
async def salva_config(
    data: ConfigPickleballSchema, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")
):
    """Pesi, punti e limiti: la classifica viene ricalcolata con i nuovi valori."""
    return await TorneiService(db).salva_config(data)


# ─── Tornei ─────────────────────────────────────────────────────────────────

@dirigenza_router.get("/tornei", response_model=list[TorneoResponse])
async def lista_tornei(_=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    return await TorneiService(db).lista()


@dirigenza_router.post("/tornei", response_model=TorneoResponse, status_code=201)
async def crea_torneo(data: TorneoCreate, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    return await TorneiService(db).crea(data)


@dirigenza_router.get("/tornei/{torneo_id}", response_model=TorneoDettaglioResponse)
async def dettaglio_torneo(torneo_id: UUID, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    return await TorneiService(db).dettaglio(torneo_id)


@dirigenza_router.put("/tornei/{torneo_id}", response_model=TorneoResponse)
async def aggiorna_torneo(
    torneo_id: UUID, data: TorneoUpdate, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    return await TorneiService(db).aggiorna(torneo_id, data)


@dirigenza_router.delete("/tornei/{torneo_id}", status_code=204)
async def elimina_torneo(torneo_id: UUID, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")):
    """Elimina il torneo con le sue partite e i piazzamenti; la classifica viene ricalcolata."""
    await TorneiService(db).elimina(torneo_id)


@dirigenza_router.post("/tornei/{torneo_id}/import", response_model=ImportRisultatiResponse)
async def importa_risultati(
    torneo_id: UUID,
    file: UploadFile = File(...),
    conferma: bool = Form(False),
    user: dict = RequireStaff,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Risultati da file CSV: anteprima (conferma=false) o importazione. Chi non è socio diventa ospite."""
    content = await file.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File troppo grande (massimo 1 MB).")
    return await TorneiService(db).importa(torneo_id, content, conferma, await _operatore_id(user, db))


@dirigenza_router.post("/tornei/{torneo_id}/piazzamenti/ricalcola", response_model=list[PiazzamentoResponse])
async def ricalcola_piazzamenti(torneo_id: UUID, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    """Ricava di nuovo i piazzamenti dalle partite (le correzioni manuali restano)."""
    service = TorneiService(db)
    await service.calcola_piazzamenti(torneo_id)
    return (await service.dettaglio(torneo_id)).piazzamenti


@dirigenza_router.put("/tornei/{torneo_id}/piazzamenti", response_model=list[PiazzamentoResponse])
async def imposta_piazzamento(
    torneo_id: UUID, data: PiazzamentoUpdate, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    return await TorneiService(db).imposta_piazzamento(torneo_id, data)


# ─── Ospiti ─────────────────────────────────────────────────────────────────

@dirigenza_router.get("/ospiti", response_model=list[OspiteResponse])
async def lista_ospiti(_=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    return await TorneiService(db).lista_ospiti()


@dirigenza_router.post("/ospiti", response_model=OspiteResponse, status_code=201)
async def crea_ospite(data: OspiteCreate, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    return await TorneiService(db).crea_ospite(data)


@dirigenza_router.put("/ospiti/{ospite_id}", response_model=OspiteResponse)
async def aggiorna_ospite(
    ospite_id: UUID, data: OspiteUpdate, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    return await TorneiService(db).aggiorna_ospite(ospite_id, data)


@dirigenza_router.delete("/ospiti/{ospite_id}", status_code=204)
async def elimina_ospite(ospite_id: UUID, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    await TorneiService(db).elimina_ospite(ospite_id)


@dirigenza_router.post("/ospiti/{ospite_id}/invita", response_model=OspiteResponse)
async def invita_ospite(ospite_id: UUID, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")):
    """Email di invito a iscriversi alla community (solo se l'ospite ha lasciato l'email)."""
    return await TorneiService(db).invita_ospite(ospite_id)


@dirigenza_router.post("/ospiti/{ospite_id}/collega", status_code=204)
async def collega_ospite(
    ospite_id: UUID, data: CollegaOspiteRequest, _=RequireStaff, db: AsyncSession = Depends(get_db, scope="function")
):
    """L'ospite si è iscritto: partite e piazzamenti passano al socio."""
    await TorneiService(db).collega_ospite(ospite_id, data.socio_id)


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
