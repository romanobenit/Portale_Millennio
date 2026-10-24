import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.database import Base

FormatoPartita = Enum("singolo", "doppio", name="formato_partita")
StatoPartita = Enum("in_attesa_conferma", "confermata", "contestata", "annullata", name="stato_partita")


class PartitaPickleball(Base):
    __tablename__ = "partite_pickleball"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formato = Column(FormatoPartita, nullable=False)
    data = Column(Date, nullable=False, index=True)
    # Punteggi dei game, dal punto di vista delle squadre A e B: [[11, 7], [9, 11], [11, 5]]
    punteggi = Column(JSONB, nullable=False)
    vincitore = Column(String(1), nullable=False)  # "a" | "b"
    stato = Column(StatoPartita, nullable=False, default="in_attesa_conferma")
    torneo = Column(String, nullable=True)
    evento_id = Column(UUID(as_uuid=True), ForeignKey("eventi_campo.id"), nullable=True)
    inserita_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    inserita_da_dirigenza = Column(Boolean, nullable=False, default=False)
    confermata_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    confermata_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GiocatorePartita(Base):
    """Giocatore di una partita, con il punteggio prima/dopo (valorizzati solo per le partite confermate)."""
    __tablename__ = "partite_pickleball_giocatori"
    __table_args__ = (PrimaryKeyConstraint("partita_id", "socio_id"),)

    partita_id = Column(UUID(as_uuid=True), ForeignKey("partite_pickleball.id", ondelete="CASCADE"), nullable=False)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    squadra = Column(String(1), nullable=False)  # "a" | "b"
    rating_prima = Column(Numeric(7, 2), nullable=True)
    rating_dopo = Column(Numeric(7, 2), nullable=True)


class RatingPickleball(Base):
    """Punteggio attuale (Elo interno del club) per socio e formato. Ricalcolato dalle partite confermate."""
    __tablename__ = "rating_pickleball"
    __table_args__ = (PrimaryKeyConstraint("socio_id", "formato"),)

    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False)
    formato = Column(FormatoPartita, nullable=False)
    rating = Column(Numeric(7, 2), nullable=False)
    rating_max = Column(Numeric(7, 2), nullable=False)
    partite = Column(Integer, nullable=False, default=0)
    vittorie = Column(Integer, nullable=False, default=0)
    ultima_partita = Column(Date, nullable=True)


class ProfiloAtleta(Base):
    __tablename__ = "profili_atleta"

    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), primary_key=True)
    visibile_in_classifica = Column(Boolean, nullable=False, default=True)
    obiettivo_singolo = Column(SmallInteger, nullable=True)
    obiettivo_doppio = Column(SmallInteger, nullable=True)
    obiettivo_partite_mese = Column(SmallInteger, nullable=True)
    dupr_id = Column(String, nullable=True)
    dupr_singolo = Column(Numeric(4, 3), nullable=True)
    dupr_doppio = Column(Numeric(4, 3), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
