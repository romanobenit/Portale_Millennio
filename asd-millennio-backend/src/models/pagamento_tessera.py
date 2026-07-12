import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base

StatoPagamentoTessera = Enum(
    "in_attesa_pagamento",
    "pagato",
    "rimborsato",
    "erogazione_liberale",  # tesseramento rifiutato dallo staff: quota NON rimborsata
    name="stato_pagamento_tessera",
)


class PagamentoTessera(Base):
    """
    Pagamento della quota associativa (Stripe). Alla conferma del pagamento la
    tessera collegata diventa 'attiva' in via provvisoria (verifica_stato='in_verifica').
    Se lo staff rifiuta la verifica, lo stato passa a 'erogazione_liberale'.
    """
    __tablename__ = "pagamento_tessera"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tessera_id = Column(UUID(as_uuid=True), ForeignKey("tessere.id"), nullable=False, index=True)
    # chi paga: il socio stesso, o il tutore in caso di minore
    pagante_socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False)
    stripe_session_id = Column(String, unique=True, nullable=False)
    stripe_payment_id = Column(String, nullable=True)
    importo_eur = Column(Numeric(10, 2), nullable=False)
    stato = Column(StatoPagamentoTessera, nullable=False, default="in_attesa_pagamento")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tessera = relationship("Tessera", foreign_keys=[tessera_id])
