import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from core.database import Base

StatoAcquisto = Enum(
    "in_attesa_pagamento", "pagato", "mintato", "fallito", "rimborsato",
    name="stato_acquisto"
)


class AcquistoNFT(Base):
    __tablename__ = "acquisti_nft"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    stripe_session_id = Column(String, unique=True, nullable=False)
    stripe_payment_id = Column(String, nullable=True)
    token_id = Column(Integer, unique=True, nullable=True)
    contract_address = Column(String, nullable=True)
    ipfs_uri = Column(String, nullable=True)
    ical_sha256 = Column(String, nullable=True)
    importo_eur = Column(Numeric(10, 2), nullable=False)
    stato = Column(StatoAcquisto, nullable=False, default="in_attesa_pagamento")
    acquisto_per_minore = Column(Boolean, default=False)
    minore_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    wallet_address = Column(String, nullable=True)
    metadati_json = Column(Text, nullable=True)
    ical_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    socio = relationship("Socio", back_populates="acquisti_nft", foreign_keys=[socio_id])
    minore = relationship("Socio", foreign_keys=[minore_id])
    slot_links = relationship("AcquistoNFTSlot", back_populates="acquisto")


class AcquistoNFTSlot(Base):
    __tablename__ = "acquisto_nft_slots"

    acquisto_nft_id = Column(UUID(as_uuid=True), ForeignKey("acquisti_nft.id"), primary_key=True)
    slot_calendario_id = Column(UUID(as_uuid=True), ForeignKey("slot_calendario.id"), primary_key=True)
    ore_acquistate = Column(ARRAY(Integer), nullable=False, default=list)

    acquisto = relationship("AcquistoNFT", back_populates="slot_links")
    slot = relationship("SlotCalendario", back_populates="acquisto_nft_slots")


class AccessoLog(Base):
    __tablename__ = "accesso_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(Integer, nullable=False, index=True)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    slot_key = Column(String, nullable=False)
    verificato_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    esito = Column(
        Enum("valido", "non_valido", "slot_errato", "tessera_scaduta", name="esito_accesso"),
        nullable=False,
    )
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    note = Column(Text, nullable=True)
