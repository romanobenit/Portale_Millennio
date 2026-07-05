from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from models.acquisto_nft import AcquistoNFT, AcquistoNFTSlot
from models.pricing_rule import PricingRule
from models.slot_calendario import SlotCalendario
from modules.calendario.pricing import PricingEngine
from schemas.dirigenza import (
    DashboardFundraising,
    OrePerFascia,
    PricingRuleCreate,
    PricingRuleUpdate,
    RendicontoAnnuale,
    RendicontoFascia,
    SimulazioneRequest,
    SimulazioneResponse,
    TopVendita,
)

settings = get_settings()

FASCE = ("notte", "mattina", "pomeriggio")
ORE_TOTALI_FASCIA = {"notte": 8, "mattina": 5, "pomeriggio": 2}

# Periodo di vendita Palasirio — letto da env
PERIODO_INIZIO = date.fromisoformat(settings.calendario_inizio)  # 2027-01-01
PERIODO_FINE   = date.fromisoformat(settings.calendario_fine)    # 2042-12-31


class DirigenzaService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Pricing rules CRUD ───────────────────────────────────────────────────

    async def lista_pricing_rules(self) -> list[PricingRule]:
        result = await self.db.execute(
            select(PricingRule).order_by(PricingRule.tipo, PricingRule.fascia, PricingRule.soglia_min)
        )
        return list(result.scalars().all())

    async def crea_pricing_rule(self, data: PricingRuleCreate) -> PricingRule:
        rule = PricingRule(id=uuid.uuid4(), **data.model_dump())
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def aggiorna_pricing_rule(self, rule_id: uuid.UUID, data: PricingRuleUpdate) -> PricingRule:
        result = await self.db.execute(select(PricingRule).where(PricingRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            from fastapi import HTTPException, status
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Regola non trovata")
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(rule, k, v)
        await self.db.flush()
        return rule

    async def disattiva_pricing_rule(self, rule_id: uuid.UUID) -> PricingRule:
        return await self.aggiorna_pricing_rule(rule_id, PricingRuleUpdate(attivo=False))

    # ─── Simulatore prezzi ────────────────────────────────────────────────────

    async def simula_prezzo(self, req: SimulazioneRequest) -> SimulazioneResponse:
        data_slot = req.data  # già un date, validato da Pydantic
        giorni_mancanti = max(0, (data_slot - date.today()).days)

        engine = PricingEngine(self.db)
        info = await engine.calcola_prezzo_ora(req.fascia, data_slot)

        # Calcola % libere effettiva sul MESE dello slot (coerente con il pricing)
        primo = date(data_slot.year, data_slot.month, 1)
        ultimo = date(data_slot.year, data_slot.month, monthrange(data_slot.year, data_slot.month)[1])
        result = await self.db.execute(
            select(func.sum(SlotCalendario.ore_totali)).where(
                and_(
                    SlotCalendario.fascia == req.fascia,
                    SlotCalendario.data >= primo,
                    SlotCalendario.data <= ultimo,
                )
            )
        )
        ore_tot = int(result.scalar() or 0)
        result2 = await self.db.execute(
            select(SlotCalendario.ore_vendute).where(
                and_(
                    SlotCalendario.fascia == req.fascia,
                    SlotCalendario.data >= primo,
                    SlotCalendario.data <= ultimo,
                )
            )
        )
        ore_vend = sum(len(r.ore_vendute or []) for r in result2)
        pct_libere = ((ore_tot - ore_vend) / ore_tot * 100) if ore_tot else None

        return SimulazioneResponse(
            fascia=req.fascia,
            data=data_slot,
            tariffa_base=info["tariffa_base"],
            moltiplicatore_data=info["moltiplicatore_data"],
            moltiplicatore_scarsita=info["moltiplicatore_scarsita"],
            sconto_promo_pct=info["sconto_promo_pct"],
            prezzo_ora=info["prezzo_ora"],
            giorni_mancanti=giorni_mancanti,
            pct_libere_effettiva=round(pct_libere, 1) if pct_libere is not None else None,
        )

    # ─── Fundraising dashboard ────────────────────────────────────────────────

    async def dashboard_fundraising(self) -> DashboardFundraising:
        # Totale raccolto
        result = await self.db.execute(
            select(func.sum(AcquistoNFT.importo_eur), func.count(AcquistoNFT.id)).where(
                AcquistoNFT.stato.in_(["pagato", "mintato"])
            )
        )
        row = result.one()
        totale_eur = float(row[0] or 0)
        n_nft = int(row[1] or 0)
        obiettivo = float(settings.fundraising_target_eur)
        percentuale = (totale_eur / obiettivo * 100) if obiettivo else 0

        # Ore vendute / totali periodo per fascia
        ore_vendute: dict[str, int] = {}
        ore_disponibili: dict[str, int] = {}
        ore_totali_periodo: dict[str, int] = {}
        for fascia in FASCE:
            result_f = await self.db.execute(
                select(SlotCalendario.ore_vendute, SlotCalendario.ore_totali).where(
                    and_(
                        SlotCalendario.fascia == fascia,
                        SlotCalendario.data >= PERIODO_INIZIO,
                        SlotCalendario.data <= PERIODO_FINE,
                    )
                )
            )
            rows_f = list(result_f)
            ore_vend = sum(len(r.ore_vendute or []) for r in rows_f)
            ore_tot = sum(int(r.ore_totali or 0) for r in rows_f)
            ore_vendute[fascia] = ore_vend
            ore_disponibili[fascia] = ore_tot - ore_vend
            ore_totali_periodo[fascia] = ore_tot

        pct_riempimento = {
            f: round(ore_vendute[f] / ore_totali_periodo[f] * 100, 2)
            if ore_totali_periodo[f] > 0 else 0.0
            for f in FASCE
        }

        # Incassi ultimi 30 giorni (cutoff calcolato in Python: evita CAST a NullType)
        cutoff_30gg = datetime.now(timezone.utc) - timedelta(days=30)
        result_30 = await self.db.execute(
            select(
                func.date(AcquistoNFT.created_at).label("data"),
                func.sum(AcquistoNFT.importo_eur).label("importo"),
            ).where(
                and_(
                    AcquistoNFT.stato.in_(["pagato", "mintato"]),
                    AcquistoNFT.created_at >= cutoff_30gg,
                )
            ).group_by(func.date(AcquistoNFT.created_at))
            .order_by(func.date(AcquistoNFT.created_at))
        )
        incassi_30gg = [
            {"data": str(r.data), "importo": float(r.importo or 0)}
            for r in result_30
        ]

        # Top 5 vendite per importo — unica query con JOIN per evitare N+1
        from sqlalchemy import literal_column
        result_top = await self.db.execute(
            select(
                AcquistoNFT.id,
                AcquistoNFT.importo_eur,
                AcquistoNFT.token_id,
                SlotCalendario.fascia,
                SlotCalendario.data,
                func.count(literal_column("1")).label("n_ore"),
            )
            .join(AcquistoNFTSlot, AcquistoNFTSlot.acquisto_nft_id == AcquistoNFT.id, isouter=True)
            .join(SlotCalendario, AcquistoNFTSlot.slot_calendario_id == SlotCalendario.id, isouter=True)
            .where(AcquistoNFT.stato.in_(["pagato", "mintato"]))
            .group_by(AcquistoNFT.id, AcquistoNFT.importo_eur, AcquistoNFT.token_id,
                      SlotCalendario.fascia, SlotCalendario.data)
            .order_by(AcquistoNFT.importo_eur.desc())
            .limit(5)
        )
        top_5: list[TopVendita] = []
        for row in result_top:
            top_5.append(TopVendita(
                data=str(row.data) if row.data else "—",
                fascia=row.fascia if row.fascia else "—",
                ore=int(row.n_ore or 0),
                importo=float(row.importo_eur),
                token_id=row.token_id,
            ))

        return DashboardFundraising(
            totale_raccolto_eur=totale_eur,
            obiettivo_eur=obiettivo,
            percentuale=round(percentuale, 2),
            nft_emessi_totali=n_nft,
            periodo_inizio=PERIODO_INIZIO.isoformat(),
            periodo_fine=PERIODO_FINE.isoformat(),
            ore_vendute=OrePerFascia(**{f: ore_vendute[f] for f in FASCE}),
            ore_disponibili=OrePerFascia(**{f: ore_disponibili[f] for f in FASCE}),
            ore_totali_periodo=OrePerFascia(**{f: ore_totali_periodo[f] for f in FASCE}),
            pct_riempimento=pct_riempimento,
            incassi_30gg=incassi_30gg,
            top_5_vendite=top_5,
        )

    # ─── Rendiconto annuale ────────────────────────────────────────────────────

    async def rendiconto_annuale(self, anno: int) -> RendicontoAnnuale:
        # Anno civile (Jan 1 – Dec 31), non "anno sportivo"
        anno_inizio = date(anno, 1, 1)
        anno_fine   = date(anno, 12, 31)

        fasce_out: list[RendicontoFascia] = []
        totale_nft = 0

        for fascia in FASCE:
            result = await self.db.execute(
                select(SlotCalendario.ore_vendute, SlotCalendario.ore_totali).where(
                    and_(
                        SlotCalendario.fascia == fascia,
                        SlotCalendario.data >= anno_inizio,
                        SlotCalendario.data <= anno_fine,
                    )
                )
            )
            rows = list(result)
            ore_vend = sum(len(r.ore_vendute or []) for r in rows)
            ore_tot = sum(int(r.ore_totali or 0) for r in rows)
            fasce_out.append(RendicontoFascia(
                fascia=fascia,
                ore_vendute=ore_vend,
                ore_totali_stagione=ore_tot,
                ricavi_lordi=0.0,
            ))

        # Ricavi dagli acquisti nell'anno civile
        result_acq = await self.db.execute(
            select(func.sum(AcquistoNFT.importo_eur), func.count(AcquistoNFT.id)).where(
                and_(
                    AcquistoNFT.stato.in_(["pagato", "mintato"]),
                    AcquistoNFT.created_at >= datetime(anno, 1, 1, tzinfo=timezone.utc),
                    AcquistoNFT.created_at < datetime(anno + 1, 1, 1, tzinfo=timezone.utc),
                )
            )
        )
        row_acq = result_acq.one()
        totale_ricavi = Decimal(str(row_acq[0] or 0))
        totale_nft = int(row_acq[1] or 0)

        # Ricavi per fascia: allocazione PER-ACQUISTO (non globale).
        # Ogni acquisto distribuisce il proprio importo tra le fasce dei suoi slot,
        # pesato su ore × tariffa_base. Esatto per acquisti mono-fascia (la maggioranza),
        # stima proporzionale solo per quelli misti. NB: l'importo esatto per-fascia non
        # è persistito a granularità slot — per un dato certificato al centesimo servirebbe
        # salvare il costo per slot al momento dell'acquisto.
        TARIFFA_BASE = {"notte": Decimal("15"), "mattina": Decimal("20"), "pomeriggio": Decimal("25")}
        alloc_rows = await self.db.execute(
            select(
                AcquistoNFT.id,
                AcquistoNFT.importo_eur,
                SlotCalendario.fascia,
                func.coalesce(func.cardinality(AcquistoNFTSlot.ore_acquistate), 0),
            )
            .join(AcquistoNFTSlot, AcquistoNFTSlot.acquisto_nft_id == AcquistoNFT.id)
            .join(SlotCalendario, AcquistoNFTSlot.slot_calendario_id == SlotCalendario.id)
            .where(and_(
                AcquistoNFT.stato.in_(["pagato", "mintato"]),
                AcquistoNFT.created_at >= datetime(anno, 1, 1, tzinfo=timezone.utc),
                AcquistoNFT.created_at < datetime(anno + 1, 1, 1, tzinfo=timezone.utc),
            ))
        )
        importi: dict = {}
        ore_acq_fascia: dict = {}
        for aid, importo, fascia, n_ore in alloc_rows:
            importi[aid] = Decimal(str(importo or 0))
            ore_acq_fascia.setdefault(aid, {})
            ore_acq_fascia[aid][fascia] = ore_acq_fascia[aid].get(fascia, 0) + int(n_ore or 0)

        ricavi_fascia = {f: Decimal("0") for f in FASCE}
        for aid, fasce_ore in ore_acq_fascia.items():
            pesi = {f: Decimal(n) * TARIFFA_BASE.get(f, Decimal("0")) for f, n in fasce_ore.items()}
            tot_peso = sum(pesi.values()) or Decimal("1")
            for f, p in pesi.items():
                if f in ricavi_fascia:
                    ricavi_fascia[f] += importi[aid] * p / tot_peso

        for f in fasce_out:
            f.ricavi_lordi = float(ricavi_fascia.get(f.fascia, Decimal("0")).quantize(Decimal("0.01")))

        return RendicontoAnnuale(
            anno=anno,
            periodo_inizio=anno_inizio.isoformat(),
            periodo_fine=anno_fine.isoformat(),
            fasce=fasce_out,
            totale_ricavi=float(totale_ricavi),
            totale_nft=totale_nft,
            generato_il=datetime.now(timezone.utc).isoformat(),
        )
