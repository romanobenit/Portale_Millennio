import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from core.database import Base


class Socio(Base):
    __tablename__ = "soci"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    cognome = Column(String, nullable=False)
    data_nascita = Column(Date, nullable=False)
    codice_fiscale = Column(String(16), unique=True, nullable=False)
    indirizzo = Column(Text)
    email = Column(String, unique=True, nullable=False)
    telefono = Column(String)
    foto_url = Column(Text)
    is_minor = Column(Boolean, default=False, nullable=False)
    tutore_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    sport = Column(ARRAY(String), default=list)
    keycloak_user_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # updated_at è gestito dal trigger PostgreSQL (migration) — non usare onupdate qui per evitare conflitti
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tutore = relationship("Socio", remote_side="Socio.id", foreign_keys=[tutore_id], backref="minori")
    tessere = relationship("Tessera", back_populates="socio", foreign_keys="Tessera.socio_id")
    consensi = relationship("Consenso", back_populates="socio", foreign_keys="Consenso.socio_id")
    acquisti_nft = relationship("AcquistoNFT", back_populates="socio", foreign_keys="AcquistoNFT.socio_id")
