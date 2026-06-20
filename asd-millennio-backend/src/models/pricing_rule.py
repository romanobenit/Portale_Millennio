import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

TipoPricingRule = Enum(
    "tariffa_base", "leva_data", "leva_scarsita", "sconto_promo",
    name="tipo_pricing_rule",
)

FasciaOrariaOpt = Enum("notte", "mattina", "pomeriggio", name="fascia_oraria_opt")


class PricingRule(Base):
    """
    Regola di pricing gestita dalla dashboard dirigenza.
    Tipi:
      tariffa_base → valore = €/ora base per la fascia
      leva_data    → soglia_min/max = giorni mancanti, valore = moltiplicatore
      leva_scarsita → soglia_min/max = % ore libere (0-100), valore = moltiplicatore
      sconto_promo → valore = percentuale sconto (0-100), fascia nullable = globale
    """
    __tablename__ = "pricing_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(TipoPricingRule, nullable=False)
    fascia = Column(FasciaOrariaOpt, nullable=True)   # null = tutte le fasce
    soglia_min = Column(Numeric(8, 2), nullable=True)
    soglia_max = Column(Numeric(8, 2), nullable=True)
    valore = Column(Numeric(10, 4), nullable=False)
    attivo = Column(Boolean, nullable=False, default=True)
    nome = Column(String(200), nullable=False)
    valido_fino_a = Column(String(10), nullable=True)   # ISO date YYYY-MM-DD, null = nessuna scadenza
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
