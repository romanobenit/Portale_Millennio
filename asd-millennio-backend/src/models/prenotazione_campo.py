import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, SmallInteger, String, Text, Date, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base

StatoPrenotazione = Enum(
    "bloccata",
    "confermata",
    "cancellata",
    "scaduta",
    name="stato_prenotazione",
)


class PrenotazioneCampo(Base):
    """
    Singola prenotazione di un campo (fascia oraria specifica in una data specifica).
    Diventa 'confermata' solo dopo il pagamento Stripe.
    """
    __tablename__ = "prenotazioni_campo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("slot_template_campo.id"), nullable=False)
    data = Column(Date, nullable=False, index=True)
    ora_inizio = Column(Time, nullable=False)
    ora_fine = Column(Time, nullable=False)
    campo = Column(SmallInteger, nullable=False)   # numero campo assegnato (1…num_campi)
    importo_eur = Column(Numeric(8, 2), nullable=False)
    stato = Column(StatoPrenotazione, nullable=False, default="bloccata")
    stripe_session_id = Column(String, unique=True, nullable=True)
    # scadenza del lock: la prenotazione 'bloccata' è valida solo fino a qui
    bloccata_fino_a = Column(DateTime(timezone=True), nullable=True)
    # limite oltre il quale non è più possibile cancellare
    cancellabile_fino_a = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    template = relationship("SlotTemplateCampo", back_populates="prenotazioni")
    socio = relationship("Socio")
