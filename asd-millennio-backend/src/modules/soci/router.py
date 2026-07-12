from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import storage
from core.database import get_db
from core.security import RequireDirigenza, RequireStaff, get_current_user
from models.consenso import Consenso
from models.documento_socio import DocumentoSocio
from models.tessera import Tessera
from modules.soci.repository import SociRepository
from modules.soci.service import SociService
from modules.soci.tesseramento_service import TesseramentoService
from schemas.consensi import ConsensoCreate, ConsensoResponse
from schemas.soci import SocioCreate, SocioListResponse, SocioResponse, SocioUpdate
from schemas.tesseramento import (
    DocumentoResponse,
    MinoreCreate,
    SocioOnboarding,
    TesseramentoCheckoutResponse,
    TesseramentoDaVerificare,
    TesseramentoRequest,
)
from schemas.tessere import TesseraCreate, TesseraResponse, TesseraVerificaResponse

router = APIRouter(prefix="/soci", tags=["M01 — Soci"])


async def _require_own_or_staff(socio_id: UUID, user: dict, db: AsyncSession) -> None:
    """
    Consente l'accesso al proprio profilo, a quello di un proprio minore (tutore),
    oppure a chi ha ruolo staff/dirigenza/allenatore.
    """
    realm_roles: list[str] = user.get("realm_access", {}).get("roles", [])
    if any(r in realm_roles for r in ("staff", "dirigenza", "allenatore")):
        return
    repo = SociRepository(db)
    socio = await repo.get_by_keycloak_id(user["sub"])
    if socio and socio.id == socio_id:
        return
    if socio:
        target = await repo.get_by_id(socio_id)
        if target and target.tutore_id == socio.id:  # tutore del minore
            return
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


# ─── Onboarding self-service (adulto) ──────────────────────────────────────────

@router.post("/me", response_model=SocioResponse, status_code=201)
async def crea_profilo_self(
    data: SocioOnboarding,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Primo accesso: l'adulto crea il proprio profilo (una volta sola)."""
    return await TesseramentoService(db).crea_profilo_self(user["sub"], user.get("email"), data)


async def _socio_target(user: dict, db: AsyncSession, socio_id: UUID | None):
    """Ritorna (me, target): target è il proprio profilo o un proprio minore."""
    me = await SociRepository(db).get_by_keycloak_id(user["sub"])
    if not me:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo non trovato")
    if socio_id is None or socio_id == me.id:
        return me, me
    minore = await SociRepository(db).get_by_id(socio_id)
    if not minore or minore.tutore_id != me.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Accesso negato")
    return me, minore


@router.post("/me/documenti", response_model=DocumentoResponse, status_code=201)
async def carica_documento_self(
    tipo: str = Query(..., pattern="^(identita|tutela)$"),
    socio_id: UUID | None = Query(None, description="socio destinatario (default: il proprio; per minori il figlio)"),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Carica un documento sensibile (cifrato) per sé o per un proprio minore."""
    me, target = await _socio_target(user, db, socio_id)
    content = await file.read(storage.MAX_DOC_BYTES + 1)
    return await TesseramentoService(db).carica_documento(
        target.id, me.id, tipo,
        file.filename or "documento",
        file.content_type or "application/octet-stream",
        content,
    )


@router.get("/documenti/{doc_id}")
async def scarica_documento(
    doc_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scarica un documento (decifrato). Solo proprietario/tutore o staff."""
    doc = (await db.execute(
        select(DocumentoSocio).where(DocumentoSocio.id == doc_id)
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Documento non trovato")

    realm_roles: list[str] = user.get("realm_access", {}).get("roles", [])
    if not any(r in realm_roles for r in ("staff", "dirigenza")):
        repo = SociRepository(db)
        me = await repo.get_by_keycloak_id(user["sub"])
        intestatario = await repo.get_by_id(doc.socio_id)
        # proprietario del documento, oppure tutore del minore intestatario
        own = me and doc.socio_id == me.id
        tutore = me and intestatario and intestatario.tutore_id == me.id
        if not (own or tutore):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Accesso negato")
    try:
        content = storage.leggi_documento(doc.storage_path)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_410_GONE, detail="File non più disponibile")
    return Response(
        content=content,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


@router.post("/me/tesseramento", response_model=TesseramentoCheckoutResponse)
async def avvia_tesseramento_self(
    data: TesseramentoRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Avvia il tesseramento per una categoria: crea la tessera e la sessione di pagamento della quota."""
    me = await SociRepository(db).get_by_keycloak_id(user["sub"])
    if not me:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo non trovato")
    return await TesseramentoService(db).avvia_tesseramento(me, data.categoria, is_minore=False)


# ─── Minori (gestiti dal tutore) ───────────────────────────────────────────────

@router.post("/me/minori", response_model=SocioResponse, status_code=201)
async def aggiungi_minore(
    data: MinoreCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Il tutore aggiunge un figlio minorenne (senza login proprio)."""
    me = await SociRepository(db).get_by_keycloak_id(user["sub"])
    if not me:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo non trovato")
    return await TesseramentoService(db).crea_minore(me, data)


@router.get("/me/minori", response_model=list[SocioResponse])
async def lista_miei_minori(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    me = await SociRepository(db).get_by_keycloak_id(user["sub"])
    if not me:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo non trovato")
    return await SociService(db).lista_minori(me.id)


@router.post("/me/minori/{minore_id}/tesseramento", response_model=TesseramentoCheckoutResponse)
async def avvia_tesseramento_minore(
    minore_id: UUID,
    data: TesseramentoRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Avvia il tesseramento di un proprio minore (pagato dal tutore)."""
    me, minore = await _socio_target(user, db, minore_id)
    if not minore.is_minor:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Il profilo indicato non è un minore")
    return await TesseramentoService(db).avvia_tesseramento(
        minore, data.categoria, is_minore=True, pagante_socio_id=me.id
    )


# ─── Verifica tesseramenti (staff) ─────────────────────────────────────────────

@router.get("/verifiche", response_model=list[TesseramentoDaVerificare])
async def lista_tesseramenti_da_verificare(
    _user: dict = RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    """Coda dei tesseramenti in via provvisoria da confermare (staff)."""
    return await TesseramentoService(db).lista_da_verificare()


@router.post("/verifiche/{tessera_id}/conferma", status_code=status.HTTP_204_NO_CONTENT)
async def conferma_tesseramento(
    tessera_id: UUID,
    user: dict = RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    verificatore = await SociRepository(db).get_by_keycloak_id(user["sub"])
    await TesseramentoService(db).conferma_verifica(tessera_id, verificatore.id if verificatore else None)


@router.post("/verifiche/{tessera_id}/rifiuta", status_code=status.HTTP_204_NO_CONTENT)
async def rifiuta_tesseramento(
    tessera_id: UUID,
    user: dict = RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    """Rifiuta il tesseramento: la tessera decade e la quota diventa erogazione liberale."""
    verificatore = await SociRepository(db).get_by_keycloak_id(user["sub"])
    await TesseramentoService(db).rifiuta_verifica(tessera_id, verificatore.id if verificatore else None)


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
