import csv
import io
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from models.consenso import Consenso
from models.socio import Socio
from models.tessera import Tessera
from models.wallet import WalletCustodiale
from modules.soci.repository import SociRepository
from schemas.consensi import ConsensoResponse
from schemas.soci import SocioCreate, SocioListResponse, SocioResponse, SocioUpdate
from schemas.tessere import TesseraCreate, TesseraResponse, TesseraVerificaResponse

settings = get_settings()

SPORT_PREFISSI = {
    "volley": "VOL",
    "badminton": "BDM",
    "kung_fu": "KFU",
    "pickleball": "PCK",
    "sostenitore": "SOS",
}


def _calcola_scadenza_tessera(anno_sportivo: str) -> date:
    anno_fine = int(anno_sportivo.split("-")[1])
    return date(anno_fine, settings.tessera_scadenza_mese, settings.tessera_scadenza_giorno)


async def _genera_numero_tessera(db: AsyncSession, sport: str, anno_sportivo: str) -> str:
    prefisso = SPORT_PREFISSI.get(sport, "GEN")
    anno = anno_sportivo.split("-")[0]
    # FOR UPDATE serializza le emissioni concorrenti per la stessa (sport, anno).
    # Senza questo, due richieste concorrenti potrebbero generare lo stesso progressivo.
    result = await db.execute(
        select(Tessera)
        .where(Tessera.sport == sport, Tessera.anno_sportivo == anno_sportivo)
        .order_by(Tessera.numero_tessera.desc())
        .limit(1)
        .with_for_update()
    )
    ultima = result.scalar_one_or_none()
    if ultima:
        progressivo = int(ultima.numero_tessera.split("-")[-1]) + 1
    else:
        progressivo = 1
    return f"{prefisso}-{anno}-{progressivo:05d}"


class SociService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = SociRepository(db)
        self.db = db

    async def lista_soci(self, page: int, limit: int) -> SocioListResponse:
        soci, total = await self.repo.list_all(page, limit)
        return SocioListResponse(
            items=[SocioResponse.model_validate(s) for s in soci],
            total=total,
            page=page,
            limit=limit,
        )

    async def crea_socio(self, data: SocioCreate) -> SocioResponse:
        if await self.repo.get_by_cf(data.codice_fiscale):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Codice fiscale già registrato")
        if await self.repo.get_by_email(data.email):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email già registrata")
        if data.is_minor and not data.tutore_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tutore obbligatorio per i minorenni")
        socio = await self.repo.create(data)
        return SocioResponse.model_validate(socio)

    async def aggiorna_socio(self, socio_id: UUID, data: SocioUpdate) -> SocioResponse:
        socio = await self.repo.get_by_id(socio_id)
        if not socio:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")
        socio = await self.repo.update(socio, data)
        return SocioResponse.model_validate(socio)

    async def emetti_tessera(self, data: TesseraCreate) -> TesseraResponse:
        if not data.socio_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="socio_id obbligatorio")
        socio = await self.repo.get_by_id(data.socio_id)
        if not socio:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")

        anno = data.anno_sportivo or settings.anno_sportivo_corrente
        numero = await _genera_numero_tessera(self.db, data.sport, anno)
        scadenza = _calcola_scadenza_tessera(anno)

        tessera = Tessera(
            socio_id=data.socio_id,
            numero_tessera=numero,
            sport=data.sport,
            stato="in_attesa_pagamento",
            anno_sportivo=anno,
            data_scadenza=scadenza,
            data_emissione=date.today(),
        )
        self.db.add(tessera)
        await self.db.flush()
        await self.db.refresh(tessera)
        return TesseraResponse.model_validate(tessera)

    async def attiva_tessera(self, tessera_id: UUID) -> TesseraResponse:
        result = await self.db.execute(select(Tessera).where(Tessera.id == tessera_id))
        tessera = result.scalar_one_or_none()
        if not tessera:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tessera non trovata")
        tessera.stato = "attiva"
        # Imposta il link al PDF generato on-the-fly (autenticazione non richiesta — UUID non indovinabile)
        tessera.pdf_url = f"{settings.app_url}/api/v1/tessere/{tessera_id}/pdf"
        await self.db.flush()
        await self.db.refresh(tessera)
        return TesseraResponse.model_validate(tessera)

    async def lista_consensi(self, socio_id: UUID) -> list[ConsensoResponse]:
        result = await self.db.execute(
            select(Consenso).where(Consenso.socio_id == socio_id).order_by(Consenso.timestamp_firma.desc())
        )
        return [ConsensoResponse.model_validate(c) for c in result.scalars().all()]

    async def lista_minori(self, tutore_id: UUID) -> list[SocioResponse]:
        result = await self.db.execute(
            select(Socio).where(Socio.tutore_id == tutore_id)
        )
        return [SocioResponse.model_validate(s) for s in result.scalars().all()]

    async def elimina_socio(self, socio_id: UUID, richiedente_id: UUID | None, is_dirigenza: bool) -> None:
        """
        Diritto alla cancellazione GDPR (Art. 17).
        Pseudoanonimizza i dati personali del socio invece di eliminare il record,
        preservando i riferimenti ai token NFT per l'audit blockchain.
        """
        socio = await self.repo.get_by_id(socio_id)
        if not socio:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")

        if not is_dirigenza and (richiedente_id is None or socio_id != richiedente_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Permessi insufficienti")

        # Blocco: il socio ha minori associati — devono essere gestiti prima
        minori_result = await self.db.execute(
            select(Socio).where(Socio.tutore_id == socio_id)
        )
        if minori_result.scalars().first():
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Impossibile eliminare: il socio è tutore di minorenni. Rimuovi prima i minorenni.",
            )

        # Pseudoanonimizzazione — i record rimangono per l'audit blockchain
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        socio.nome = "RIMOSSO"
        socio.cognome = "RIMOSSO"
        socio.email = f"rimosso-{ts}-{str(socio_id)[:8]}@millennioasd.com"
        socio.codice_fiscale = f"RMSS{ts[:10].replace(':', '')}"[:16]
        socio.telefono = None
        socio.foto_url = None
        socio.indirizzo = None
        socio.keycloak_user_id = None

        # Revoca tutti i consensi attivi
        consensi_result = await self.db.execute(
            select(Consenso).where(Consenso.socio_id == socio_id, Consenso.revocato_at.is_(None))
        )
        now = datetime.now(timezone.utc)
        for c in consensi_result.scalars().all():
            c.revocato_at = now

        # Cancella la chiave privata del wallet custodiale (GDPR Art. 17).
        # Il record wallet rimane per la catena di audit NFT, ma la chiave non è recuperabile.
        wallet_result = await self.db.execute(
            select(WalletCustodiale).where(WalletCustodiale.socio_id == socio_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if wallet:
            wallet.encrypted_private_key = ""
            wallet.wallet_address = f"rimosso-{ts}"

        await self.db.flush()
        logger.info("Socio %s pseudoanonimizzato per richiesta GDPR Art.17", socio_id)

    async def verifica_tessera(self, tessera_id: UUID) -> TesseraVerificaResponse:
        result = await self.db.execute(
            select(Tessera).where(Tessera.id == tessera_id)
        )
        tessera = result.scalar_one_or_none()
        if not tessera:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tessera non trovata")
        socio = await self.repo.get_by_id(tessera.socio_id)
        valida = tessera.stato == "attiva" and (
            tessera.data_scadenza is None or tessera.data_scadenza >= date.today()
        )
        return TesseraVerificaResponse(
            valida=valida,
            numero_tessera=tessera.numero_tessera,
            sport=tessera.sport,
            stato=tessera.stato,
            data_scadenza=tessera.data_scadenza,
            socio_nome=socio.nome if socio else "",
            socio_cognome=socio.cognome if socio else "",
        )

    async def importa_csv(self, file: UploadFile) -> dict:
        MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB
        content = await file.read(MAX_CSV_BYTES + 1)
        if len(content) > MAX_CSV_BYTES:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File troppo grande. Limite: 5 MB.",
            )
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Il file deve essere in formato UTF-8.",
            )
        reader = csv.DictReader(io.StringIO(text))
        importati, errori = 0, []
        for i, row in enumerate(reader, start=2):
            try:
                # Savepoint per riga: un errore (es. IntegrityError) annulla SOLO
                # questa riga senza invalidare l'intera transazione di import.
                async with self.db.begin_nested():
                    data = SocioCreate(**row)
                    await self.crea_socio(data)
                importati += 1
            except HTTPException as e:
                errori.append({"riga": i, "errore": e.detail})
            except Exception:
                errori.append({"riga": i, "errore": "Dati non validi"})
        return {"importati": importati, "errori": errori}
