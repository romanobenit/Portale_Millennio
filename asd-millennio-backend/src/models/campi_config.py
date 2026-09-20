import uuid

from sqlalchemy import Column, DateTime, SmallInteger, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class CampiConfig(Base):
    """
    Configurazione della prenotazione campi — riga singleton.
    `orizzonte_giorni`: per quanti giorni in avanti da oggi la disponibilità
    è mostrata/prenotabile (prima era fisso a 60 nel frontend).
    """
    __tablename__ = "campi_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orizzonte_giorni = Column(SmallInteger, nullable=False, default=60)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
