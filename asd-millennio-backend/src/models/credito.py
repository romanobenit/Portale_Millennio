import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

TipoMovimentoCredito = Enum(
    "accredito",          # accredito manuale della dirigenza
    "storno",             # correzione in negativo della dirigenza (o rimborso Stripe di una ricarica)
    "ricarica_sede",      # versamento in sede registrato dalla dirigenza
    "ricarica_online",    # ricarica pagata con Stripe
    "pagamento_evento",   # ingresso a un evento pagato col credito
    "rimborso_evento",    # annullamento di un ingresso rimborsato in credito
    name="tipo_movimento_credito",
)


class MovimentoCredito(Base):
    """
    Registro del credito interno: solo per i servizi dell'associazione, niente
    trasferimenti fra soci né prelievi. Le righe non si modificano né si cancellano
    (lo impedisce un trigger): il saldo è la somma degli importi.
    """
    __tablename__ = "movimenti_credito"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    tipo = Column(TipoMovimentoCredito, nullable=False)
    importo_eur = Column(Numeric(10, 2), nullable=False)       # positivo = entra, negativo = esce
    saldo_dopo_eur = Column(Numeric(10, 2), nullable=False)
    causale = Column(Text, nullable=True)
    prenotazione_evento_id = Column(
        UUID(as_uuid=True), ForeignKey("prenotazioni_evento.id"), nullable=True, index=True
    )
    stripe_session_id = Column(String, unique=True, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True, index=True)
    operatore_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
