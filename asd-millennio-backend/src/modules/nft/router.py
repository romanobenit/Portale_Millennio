from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limit import limiter
from core.security import RequireDirigenza, RequireStaff, get_current_user
from modules.nft.service import NFTService
from schemas.nft import (
    AcquistoNFTRequest,
    AcquistoNFTResponse,
    DashboardFundraisingResponse,
    MioNFTResponse,
    NFTVerificaResponse,
)

router = APIRouter(prefix="/nft", tags=["M04-NFT — Raccolta fondi"])


@router.post("/acquisto", response_model=AcquistoNFTResponse, status_code=201)
@limiter.limit("10/minute")
async def avvia_acquisto_nft(
    request: Request,
    data: AcquistoNFTRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from modules.soci.repository import SociRepository
    from fastapi import HTTPException, status as http_status

    socio = await SociRepository(db).get_by_keycloak_id(user["sub"])
    if not socio:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Profilo socio non trovato")

    return await NFTService(db).avvia_acquisto(socio.id, data)


@router.get("/le-mie", response_model=list[MioNFTResponse])
@limiter.limit("30/minute")
async def le_mie_nft(
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Elenco degli NFT del socio autenticato (pagina 'I miei NFT')."""
    from modules.soci.repository import SociRepository

    socio = await SociRepository(db).get_by_keycloak_id(user["sub"])
    if not socio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profilo socio non trovato")
    return await NFTService(db).lista_miei_nft(socio.id)


@router.get("/{acquisto_id}/certificato")
@limiter.limit("20/minute")
async def scarica_certificato(
    request: Request,
    acquisto_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """PDF del certificato di sostegno — solo il proprietario dell'acquisto o lo staff."""
    from modules.soci.repository import SociRepository

    socio = await SociRepository(db).get_by_keycloak_id(user["sub"])
    roles = (user.get("realm_access") or {}).get("roles", [])
    is_staff = "staff" in roles or "dirigenza" in roles
    pdf = await NFTService(db).certificato_pdf(
        acquisto_id, socio.id if socio else None, is_staff
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="certificato-palasirio-nft-{acquisto_id}.pdf"'
        },
    )


@router.get("/verify", response_model=NFTVerificaResponse)
@limiter.limit("30/minute")
async def verifica_accesso_nft(
    request: Request,
    token_id: int = Query(...),
    slot_key: str = Query(...),
    user: dict = RequireStaff,
    db: AsyncSession = Depends(get_db),
):
    """Verifica accesso al Palasirio tramite QR code — solo staff."""
    from modules.soci.repository import SociRepository

    verificatore = await SociRepository(db).get_by_keycloak_id(user["sub"])
    verificato_da = verificatore.id if verificatore else None
    return await NFTService(db).verifica_accesso(token_id, slot_key, verificato_da)


@router.get("/dashboard", response_model=DashboardFundraisingResponse)
@limiter.limit("30/minute")
async def dashboard_fundraising(
    request: Request,
    _user=RequireDirigenza,
    db: AsyncSession = Depends(get_db),
):
    """Mantiene la compatibilità — usa /api/v1/dirigenza/fundraising per la dashboard completa."""
    return await NFTService(db).dashboard_fundraising()
