import uuid

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base

StatoTessera = Enum(
    "bozza", "in_attesa_pagamento", "attiva", "scaduta", "sospesa",
    name="stato_tessera"
)


class Tessera(Base):
    __tablename__ = "tessere"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    numero_tessera = Column(String, unique=True, nullable=False)
    sport = Column(String, nullable=False)
    stato = Column(StatoTessera, nullable=False, default="bozza")
    data_emissione = Column(Date)
    data_scadenza = Column(Date)
    anno_sportivo = Column(String)
    pdf_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    socio = relationship("Socio", back_populates="tessere", foreign_keys=[socio_id])
