import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limit import limiter
from core.security import get_current_user
from modules.dirigenza.service import DirigenzaService
from modules.soci.tesseramento_service import TesseramentoService
from schemas.dirigenza import (
    DashboardFundraising,
    PricingRuleCreate,
    PricingRuleResponse,
    PricingRuleUpdate,
    RendicontoAnnuale,
    SimulazioneRequest,
    SimulazioneResponse,
)
from schemas.tesseramento import QuotaCreate, QuotaResponse, QuotaUpdate

router = APIRouter(prefix="/dirigenza", tags=["Dirigenza"])


def _require_dirigenza(user: dict = Depends(get_current_user)) -> dict:
    roles: list[str] = user.get("realm_access", {}).get("roles", [])
    if "dirigenza" not in roles and "staff" not in roles:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Accesso riservato alla dirigenza")
    return user


# ─── Dashboard fundraising ────────────────────────────────────────────────────

@router.get("/fundraising", response_model=DashboardFundraising)
@limiter.limit("30/minute")
async def dashboard_fundraising(
    request: Request,
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    return await DirigenzaService(db).dashboard_fundraising()


# ─── Pricing rules CRUD ───────────────────────────────────────────────────────

@router.get("/pricing-rules", response_model=list[PricingRuleResponse])
@limiter.limit("30/minute")
async def lista_pricing_rules(
    request: Request,
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    return await DirigenzaService(db).lista_pricing_rules()


@router.post("/pricing-rules", response_model=PricingRuleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def crea_pricing_rule(
    request: Request,
    data: PricingRuleCreate,
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        rule = await DirigenzaService(db).crea_pricing_rule(data)
    return rule


@router.put("/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
@limiter.limit("20/minute")
async def aggiorna_pricing_rule(
    request: Request,
    rule_id: uuid.UUID,
    data: PricingRuleUpdate,
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        rule = await DirigenzaService(db).aggiorna_pricing_rule(rule_id, data)
    return rule


@router.delete("/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
@limiter.limit("20/minute")
async def disattiva_pricing_rule(
    request: Request,
    rule_id: uuid.UUID,
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        rule = await DirigenzaService(db).disattiva_pricing_rule(rule_id)
    return rule


# ─── Simulatore prezzi ────────────────────────────────────────────────────────

@router.post("/pricing-simulate", response_model=SimulazioneResponse)
@limiter.limit("30/minute")
async def simula_prezzo(
    request: Request,
    data: SimulazioneRequest,
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    return await DirigenzaService(db).simula_prezzo(data)


# ─── Rendiconto annuale ────────────────────────────────────────────────────────

@router.get("/rendiconto", response_model=RendicontoAnnuale)
@limiter.limit("10/minute")
async def rendiconto(
    request: Request,
    anno: int = Query(2026, ge=2020, le=2050),
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    return await DirigenzaService(db).rendiconto_annuale(anno)


# ─── Quote tessera (dirigenza) ─────────────────────────────────────────────────

@router.get("/quote-tessera", response_model=list[QuotaResponse])
@limiter.limit("60/minute")
async def lista_quote(
    request: Request,
    anno_sportivo: str | None = Query(None),
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    return await TesseramentoService(db).lista_quote(anno_sportivo)


@router.post("/quote-tessera", response_model=QuotaResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def crea_quota(
    request: Request,
    data: QuotaCreate,
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    return await TesseramentoService(db).crea_quota(data)


@router.put("/quote-tessera/{quota_id}", response_model=QuotaResponse)
@limiter.limit("30/minute")
async def aggiorna_quota(
    request: Request,
    quota_id: uuid.UUID,
    data: QuotaUpdate,
    _user: dict = Depends(_require_dirigenza),
    db: AsyncSession = Depends(get_db),
):
    return await TesseramentoService(db).aggiorna_quota(quota_id, data)
