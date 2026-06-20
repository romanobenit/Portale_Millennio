import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base

TipoConsenso = Enum(
    "privacy", "trattamento_dati", "foto_video", "marketing",
    name="tipo_consenso"
)


class Consenso(Base):
    __tablename__ = "consensi"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    tipo = Column(TipoConsenso, nullable=False)
    testo_versione = Column(String)
    firmato_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"))
    timestamp_firma = Column(DateTime(timezone=True))
    revocato_at = Column(DateTime(timezone=True), nullable=True)

    socio = relationship("Socio", back_populates="consensi", foreign_keys=[socio_id])
    firmatario = relationship("Socio", foreign_keys=[firmato_da])
