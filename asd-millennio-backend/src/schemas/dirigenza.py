from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TipoPricingRule = Literal["tariffa_base", "leva_data", "leva_scarsita", "sconto_promo"]
FasciaOraria = Literal["notte", "mattina", "pomeriggio"]


# ─── Pricing Rules ────────────────────────────────────────────────────────────

class PricingRuleBase(BaseModel):
    tipo: TipoPricingRule
    fascia: FasciaOraria | None = None
    soglia_min: float | None = None
    soglia_max: float | None = None
    valore: float
    attivo: bool = True
    nome: str = Field(..., max_length=200)
    valido_fino_a: date | None = None
    note: str | None = None


class PricingRuleCreate(PricingRuleBase):
    pass


class PricingRuleUpdate(BaseModel):
    fascia: FasciaOraria | None = None
    soglia_min: float | None = None
    soglia_max: float | None = None
    valore: float | None = None
    attivo: bool | None = None
    nome: str | None = Field(None, max_length=200)
    valido_fino_a: date | None = None
    note: str | None = None


class PricingRuleResponse(PricingRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Simulatore prezzi ────────────────────────────────────────────────────────

class SimulazioneRequest(BaseModel):
    fascia: FasciaOraria
    data: date              # Pydantic valida il formato ISO YYYY-MM-DD automaticamente
    pct_libere_override: float | None = Field(
        None,
        description="Overridi la % ore libere per simulazione (0–100). Se null usa il dato reale.",
    )


class SimulazioneResponse(BaseModel):
    fascia: str
    data: date
    tariffa_base: float
    moltiplicatore_data: float
    moltiplicatore_scarsita: float
    sconto_promo_pct: float
    prezzo_ora: float
    giorni_mancanti: int
    pct_libere_effettiva: float | None


# ─── Fundraising dashboard ────────────────────────────────────────────────────

class OrePerFascia(BaseModel):
    notte: int
    mattina: int
    pomeriggio: int


class TopVendita(BaseModel):
    data: str
    fascia: str
    ore: int
    importo: float
    token_id: int | None


class DashboardFundraising(BaseModel):
    totale_raccolto_eur: float
    obiettivo_eur: float
    percentuale: float
    nft_emessi_totali: int
    periodo_inizio: str                 # YYYY-MM-DD
    periodo_fine: str                   # YYYY-MM-DD
    ore_vendute: OrePerFascia
    ore_disponibili: OrePerFascia
    ore_totali_periodo: OrePerFascia    # capacità totale 2027-2042
    pct_riempimento: dict[str, float]   # {"notte": 0.12, "mattina": 0.0, "pomeriggio": 0.0}
    incassi_30gg: list[dict]            # [{data, importo}]
    top_5_vendite: list[TopVendita]


# ─── Rendiconto annuale ────────────────────────────────────────────────────────

class RendicontoFascia(BaseModel):
    fascia: str
    ore_vendute: int
    ore_totali_stagione: int
    ricavi_lordi: float


class RendicontoAnnuale(BaseModel):
    anno: int                           # anno civile es. 2027
    periodo_inizio: str                 # YYYY-01-01
    periodo_fine: str                   # YYYY-12-31
    fasce: list[RendicontoFascia]
    totale_ricavi: float
    totale_nft: int
    generato_il: str
