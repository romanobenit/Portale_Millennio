import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base
from models.tessera import VerificaTessera


class TesseraEsterna(Base):
    """
    Tessera di un'altra ASD (affiliata a una federazione o a un ente di promozione
    sportiva) che dà diritto all'iscrizione community. L'iscrizione non scade;
    è la validità di questa tessera a decidere se si possono usare i campi.
    Ogni aggiornamento crea una nuova riga (lo storico resta).
    """
    __tablename__ = "tessere_esterne"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    ente = Column(String, nullable=False)
    asd_nome = Column(String, nullable=False)
    asd_codice = Column(String, nullable=True)
    numero_tessera = Column(String, nullable=False)
    disciplina = Column(String, nullable=False)
    data_scadenza = Column(Date, nullable=False)
    documento_id = Column(UUID(as_uuid=True), ForeignKey("documenti_socio.id"), nullable=True)
    verifica_stato = Column(VerificaTessera, nullable=False, default="in_verifica")
    verifica_scadenza = Column(DateTime(timezone=True), nullable=True)
    verificata_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    verificata_at = Column(DateTime(timezone=True), nullable=True)
    caricata_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
