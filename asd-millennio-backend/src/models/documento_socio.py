import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base

TipoDocumento = Enum(
    "identita",  # documento d'identità del socio (o del minore)
    "tutela",    # documento che prova la tutela del minore
    name="tipo_documento",
)


class DocumentoSocio(Base):
    """
    Documento sensibile di un socio (identità / prova tutela). Il file vero è
    cifrato su volume privato; qui vivono solo i metadati e il percorso relativo.
    """
    __tablename__ = "documenti_socio"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    tipo = Column(TipoDocumento, nullable=False)
    filename = Column(String, nullable=False)          # nome originale (per il download)
    content_type = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)      # percorso relativo del file cifrato
    size_bytes = Column(Integer, nullable=False)
    caricato_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)  # chi ha caricato (tutore)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    socio = relationship("Socio", foreign_keys=[socio_id])
