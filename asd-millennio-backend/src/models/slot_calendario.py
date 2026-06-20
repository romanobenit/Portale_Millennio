import uuid

from sqlalchemy import Column, DateTime, Enum, Integer, SmallInteger, String, Date, Time, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from core.database import Base

FasciaOraria = Enum("notte", "mattina", "pomeriggio", name="fascia_oraria")
# libero  → ore_vendute vuoto, nessun lock attivo
# parziale → alcune ore vendute, altre libere
# esaurito → tutte le ore vendute
# bloccato → lock temporaneo in corso (max 30 min)
StatoSlot = Enum("libero", "parziale", "esaurito", "bloccato", name="stato_slot")


class SlotCalendario(Base):
    """
    Un row per (data, fascia). Le ore specifiche vendute sono tracciate in ore_vendute.
    Esempio notte 00:00-07:59: ore_totali=8, ore_vendute=[0,1,2] → 3h vendute, 5h libere.
    """
    __tablename__ = "slot_calendario"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(Date, nullable=False, index=True)
    fascia = Column(FasciaOraria, nullable=False)
    ora_inizio = Column(Time, nullable=False)      # es. 00:00 per notte
    ora_fine = Column(Time, nullable=False)        # es. 07:59 per notte
    ore_totali = Column(SmallInteger, nullable=False)  # 8 notte, 5 mattina, 2 pomeriggio
    ore_vendute = Column(ARRAY(Integer), nullable=False, default=list)   # [0,1,2] = h vendute
    ore_in_lock = Column(ARRAY(Integer), nullable=False, default=list)   # lock pre-pagamento
    stato = Column(StatoSlot, nullable=False, default="libero")
    nft_token_id = Column(Integer, nullable=True)
    bloccato_fino_a = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    acquisto_nft_slots = relationship("AcquistoNFTSlot", back_populates="slot")
