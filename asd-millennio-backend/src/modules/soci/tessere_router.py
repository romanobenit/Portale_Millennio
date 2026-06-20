"""
Router separato per /tessere — espone gli endpoint pubblici di verifica e download PDF.
CLAUDE.md §M01: QR punta a GET /api/v1/tessere/{id}/verifica (endpoint pubblico).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limit import limiter
from models.tessera import Tessera
from models.socio import Socio
from modules.soci.pdf import genera_tessera_pdf
from modules.soci.service import SociService
from schemas.tessere import TesseraVerificaResponse

router = APIRouter(prefix="/tessere", tags=["M01 — Tessere (pubblico)"])


@router.get("/{tessera_id}/verifica", response_model=TesseraVerificaResponse)
@limiter.limit("30/minute")
async def verifica_tessera_pubblica(
    request: Request,
    tessera_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint pubblico — puntato dal QR code sulla tessera digitale.
    Non richiede autenticazione.
    """
    return await SociService(db).verifica_tessera(tessera_id)


@router.get("/{tessera_id}/pdf")
@limiter.limit("10/minute")
async def download_tessera_pdf(
    request: Request,
    tessera_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera e restituisce il PDF della tessera con QR code.
    L'UUID non è indovinabile — nessuna autenticazione richiesta per il download diretto.
    """
    tessera_result = await db.execute(select(Tessera).where(Tessera.id == tessera_id))
    tessera = tessera_result.scalar_one_or_none()
    if not tessera:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tessera non trovata")

    socio_result = await db.execute(select(Socio).where(Socio.id == tessera.socio_id))
    socio = socio_result.scalar_one_or_none()
    if not socio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")

    from core.config import get_settings
    settings = get_settings()
    verifica_url = f"{settings.app_url}/api/v1/tessere/{tessera_id}/verifica"

    pdf_bytes = genera_tessera_pdf(
        numero_tessera=tessera.numero_tessera,
        sport=tessera.sport,
        stato=tessera.stato,
        data_emissione=tessera.data_emissione,
        data_scadenza=tessera.data_scadenza,
        anno_sportivo=tessera.anno_sportivo,
        nome=socio.nome,
        cognome=socio.cognome,
        verifica_url=verifica_url,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="tessera-{tessera.numero_tessera}.pdf"'
        },
    )
