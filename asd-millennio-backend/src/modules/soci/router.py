from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import RequireDirigenza, RequireStaff, get_current_user
from models.consenso import Consenso
from models.tessera import Tessera
from modules.soci.repository import SociRepository
from modules.soci.service import SociService
from schemas.consensi import ConsensoCreate, ConsensoResponse
from schemas.soci import SocioCreate, SocioListResponse, SocioResponse, SocioUpdate
from schemas.tessere import TesseraCreate, TesseraResponse, TesseraVerificaResponse

router = APIRouter(prefix="/soci", tags=["M01 — Soci"])


async def _require_own_or_staff(socio_id: UUID, user: dict, db: AsyncSession) -> None:
    """Verifica che l'utente stia accedendo al proprio profilo, oppure abbia ruolo staff/dirigenza."""
    realm_roles: list[str] = user.get("realm_access", {}).get("roles", [])
    if any(r in realm_roles for r in ("staff", "dirigenza", "allenatore")):
        return
    socio = await SociRepository(db).get_by_keycloak_id(user["sub"])
    if not socio or socio.id != socio_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Accesso negato")

# ─── Soci ────────────────────────────────────────────────────────────────────

@router.get("", response_model=SocioListResponse)
async def lista_soci(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _user=RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    return await SociService(db).lista_soci(page, limit)


@router.post("", response_model=SocioResponse, status_code=201)
async def crea_socio(
    data: SocioCreate,
    _user=RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    return await SociService(db).crea_socio(data)


@router.post("/import", status_code=202)
async def importa_soci_csv(
    file: UploadFile = File(...),
    _user=RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    return await SociService(db).importa_csv(file)


@router.get("/me", response_model=SocioResponse)
async def get_me(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SociRepository(db)
    socio = await repo.get_by_keycloak_id(user["sub"])

    if not socio:
        # Primo accesso dopo creazione manuale dallo staff: cerca per email e collega l'account
        email = user.get("email")
        if email:
            socio = await repo.get_by_email(email)
        if socio and not socio.keycloak_user_id:
            socio.keycloak_user_id = user["sub"]
            await db.flush()

    if not socio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo non trovato")

    return SocioResponse.model_validate(socio)


@router.get("/{socio_id}", response_model=SocioResponse)
async def get_socio(
    socio_id: UUID,
    _user=RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    socio = await SociRepository(db).get_by_id(socio_id)
    if not socio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")
    return SocioResponse.model_validate(socio)


@router.patch("/{socio_id}", response_model=SocioResponse)
async def aggiorna_socio(
    socio_id: UUID,
    data: SocioUpdate,
    _user=RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    return await SociService(db).aggiorna_socio(socio_id, data)


# ─── Tessere ─────────────────────────────────────────────────────────────────

@router.get("/{socio_id}/tessere", response_model=list[TesseraResponse])
async def lista_tessere_socio(
    socio_id: UUID,
    stato: str | None = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista tessere di un socio, con filtro opzionale per stato (es. ?stato=attiva)."""
    await _require_own_or_staff(socio_id, user, db)
    q = select(Tessera).where(Tessera.socio_id == socio_id)
    if stato:
        q = q.where(Tessera.stato == stato)
    result = await db.execute(q)
    return [TesseraResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/{socio_id}/tessere", response_model=TesseraResponse, status_code=201)
async def emetti_tessera(
    socio_id: UUID,
    data: TesseraCreate,
    _user=RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    data.socio_id = socio_id
    return await SociService(db).emetti_tessera(data)


@router.post("/{socio_id}/tessere/{tessera_id}/attiva", response_model=TesseraResponse)
async def attiva_tessera(
    socio_id: UUID,
    tessera_id: UUID,
    _user=RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    return await SociService(db).attiva_tessera(tessera_id)


# ─── Consensi ────────────────────────────────────────────────────────────────

@router.post("/{socio_id}/consensi", response_model=ConsensoResponse, status_code=201)
async def registra_consenso(
    socio_id: UUID,
    data: ConsensoCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_own_or_staff(socio_id, user, db)
    consenso = Consenso(
        socio_id=socio_id,
        tipo=data.tipo,
        testo_versione=data.testo_versione,
        firmato_da=data.firmato_da or socio_id,
        timestamp_firma=datetime.now(timezone.utc),
    )
    db.add(consenso)
    await db.flush()
    await db.refresh(consenso)
    return ConsensoResponse.model_validate(consenso)


@router.delete("/{socio_id}/consensi/{consenso_id}", status_code=204)
async def revoca_consenso(
    socio_id: UUID,
    consenso_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_own_or_staff(socio_id, user, db)
    result = await db.execute(
        select(Consenso).where(Consenso.id == consenso_id, Consenso.socio_id == socio_id)
    )
    consenso = result.scalar_one_or_none()
    if consenso:
        consenso.revocato_at = datetime.now(timezone.utc)
        await db.flush()


@router.get("/{socio_id}/consensi", response_model=list[ConsensoResponse])
async def lista_consensi_socio(
    socio_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista consensi GDPR del socio — include attivi e revocati."""
    await _require_own_or_staff(socio_id, user, db)
    return await SociService(db).lista_consensi(socio_id)


@router.get("/{socio_id}/minori", response_model=list[SocioResponse])
async def lista_minori_tutore(
    socio_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista dei minorenni di cui il socio è tutore legale."""
    await _require_own_or_staff(socio_id, user, db)
    return await SociService(db).lista_minori(socio_id)


@router.delete("/{socio_id}", status_code=204)
async def elimina_socio(
    socio_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Diritto alla cancellazione GDPR Art. 17.
    Il socio può eliminare il proprio account; la dirigenza può eliminare qualsiasi socio.
    I dati vengono pseudoanonimizzati (non cancellati) per preservare l'audit blockchain.
    """
    realm_roles: list[str] = user.get("realm_access", {}).get("roles", [])
    is_dirigenza = "dirigenza" in realm_roles

    repo = SociRepository(db)
    richiedente = await repo.get_by_keycloak_id(user["sub"])

    if richiedente is None and not is_dirigenza:
        # L'utente non è nel DB: non può essere il proprietario dell'account target.
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Profilo richiedente non trovato")

    richiedente_id = richiedente.id if richiedente else None

    await SociService(db).elimina_socio(
        socio_id=socio_id,
        richiedente_id=richiedente_id,
        is_dirigenza=is_dirigenza,
    )
