import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Numeric, SmallInteger, String, Text, Time, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from core.database import Base


class SlotTemplateCampo(Base):
    """
    Regola ricorrente per i campi prenotabili.
    Un template definisce: giorno della settimana, fascia oraria, numero campi, costo.
    La disponibilità viene calcolata on-demand a partire da questi template.
    """
    __tablename__ = "slot_template_campo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 0=Lunedì … 6=Domenica (Python weekday())
    giorno_settimana = Column(SmallInteger, nullable=False)
    ora_inizio = Column(Time, nullable=False)
    ora_fine = Column(Time, nullable=False)
    num_campi = Column(SmallInteger, nullable=False, default=4)
    costo_ora = Column(Numeric(8, 2), nullable=False)
    sport = Column(ARRAY(String), nullable=False, default=list)
    attivo = Column(Boolean, nullable=False, default=True)
    valido_dal = Column(Date, nullable=False)
    valido_fino_al = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    prenotazioni = relationship("PrenotazioneCampo", back_populates="template")
