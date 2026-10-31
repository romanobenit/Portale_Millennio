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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.database import Base

FormatoPartita = Enum("singolo", "doppio", name="formato_partita")
StatoPartita = Enum("in_attesa_conferma", "confermata", "contestata", "annullata", name="stato_partita")
LivelloTorneo = Enum("sociale", "open", "federale", name="livello_torneo")
Piazzamento = Enum(
    "vincitore", "finalista", "semifinalista", "fase_finale", "partecipazione", "nessuno", name="piazzamento_torneo"
)
FASI = ("girone", "ottavi", "quarti", "semifinale", "finale", "altro")


class TorneoPickleball(Base):
    """Torneo (interno o esterno, es. FIBa): le sue partite pesano di più nell'Elo e danno punti al circuito."""
    __tablename__ = "tornei_pickleball"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    data = Column(Date, nullable=False, index=True)
    luogo = Column(String, nullable=True)
    livello = Column(LivelloTorneo, nullable=False, default="sociale")
    anno_sportivo = Column(String(9), nullable=False, index=True)
    concluso = Column(Boolean, nullable=False, default=False)
    url_esterno = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GiocatoreOspite(Base):
    """
    Giocatore non socio incontrato nei tornei: dati minimi, serve solo a calcolare l'Elo dei soci.
    Non compare nelle classifiche. Se si iscrive, la dirigenza lo collega al socio e la riga sparisce.
    """
    __tablename__ = "giocatori_ospiti"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    cognome = Column(String, nullable=False)
    club = Column(String, nullable=True)
    email = Column(String, nullable=True)            # solo se ha acconsentito a essere contattato
    sesso = Column(String(1), nullable=True)         # "M" | "F"
    anno_nascita = Column(SmallInteger, nullable=True)
    invitato_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PartitaPickleball(Base):
    __tablename__ = "partite_pickleball"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    formato = Column(FormatoPartita, nullable=False)
    data = Column(Date, nullable=False, index=True)
    # Punteggi dei game, dal punto di vista delle squadre A e B: [[11, 7], [9, 11], [11, 5]]
    punteggi = Column(JSONB, nullable=False)
    vincitore = Column(String(1), nullable=False)  # "a" | "b"
    stato = Column(StatoPartita, nullable=False, default="in_attesa_conferma")
    torneo = Column(String, nullable=True)                 # testo libero (partite inserite a mano)
    torneo_id = Column(
        UUID(as_uuid=True), ForeignKey("tornei_pickleball.id", ondelete="CASCADE"), nullable=True, index=True
    )
    categoria = Column(String(20), nullable=True)          # es. "SMO40", "DMO15"
    fase = Column(String(20), nullable=True)               # vedi FASI
    walkover = Column(Boolean, nullable=False, default=False)
    # Perché una partita confermata non ha mosso l'Elo ("walkover", "limite amichevoli"): derivato dal ricalcolo
    fuori_classifica = Column(String(30), nullable=True)
    evento_id = Column(UUID(as_uuid=True), ForeignKey("eventi_campo.id"), nullable=True)
    inserita_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    inserita_da_dirigenza = Column(Boolean, nullable=False, default=False)
    confermata_da = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True)
    confermata_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GiocatorePartita(Base):
    """
    Giocatore di una partita (un socio o un ospite), con il punteggio prima/dopo
    (valorizzati solo per le partite confermate che contano in classifica).
    """
    __tablename__ = "partite_pickleball_giocatori"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partita_id = Column(UUID(as_uuid=True), ForeignKey("partite_pickleball.id", ondelete="CASCADE"), nullable=False)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True, index=True)
    ospite_id = Column(UUID(as_uuid=True), ForeignKey("giocatori_ospiti.id"), nullable=True, index=True)
    squadra = Column(String(1), nullable=False)  # "a" | "b"
    rating_prima = Column(Numeric(7, 2), nullable=True)
    rating_dopo = Column(Numeric(7, 2), nullable=True)

    @property
    def giocatore_id(self):
        return self.socio_id or self.ospite_id


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


class RatingOspite(Base):
    """Elo degli ospiti: serve al calcolo, non compare in classifica."""
    __tablename__ = "rating_ospiti_pickleball"
    __table_args__ = (PrimaryKeyConstraint("ospite_id", "formato"),)

    ospite_id = Column(UUID(as_uuid=True), ForeignKey("giocatori_ospiti.id", ondelete="CASCADE"), nullable=False)
    formato = Column(FormatoPartita, nullable=False)
    rating = Column(Numeric(7, 2), nullable=False)
    partite = Column(Integer, nullable=False, default=0)
    vittorie = Column(Integer, nullable=False, default=0)


class PiazzamentoTorneo(Base):
    """Piazzamento di un giocatore in una categoria di un torneo: dà i punti del circuito."""
    __tablename__ = "piazzamenti_torneo"
    __table_args__ = (
        UniqueConstraint("torneo_id", "categoria", "socio_id", name="uq_piazzamento_socio"),
        UniqueConstraint("torneo_id", "categoria", "ospite_id", name="uq_piazzamento_ospite"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    torneo_id = Column(
        UUID(as_uuid=True), ForeignKey("tornei_pickleball.id", ondelete="CASCADE"), nullable=False, index=True
    )
    categoria = Column(String(20), nullable=False)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=True, index=True)
    ospite_id = Column(UUID(as_uuid=True), ForeignKey("giocatori_ospiti.id", ondelete="CASCADE"), nullable=True)
    piazzamento = Column(Piazzamento, nullable=False)
    manuale = Column(Boolean, nullable=False, default=False)   # corretto dalla dirigenza: il ricalcolo non lo tocca

    @property
    def giocatore_id(self):
        return self.socio_id or self.ospite_id


class ConfigPickleball(Base):
    """Impostazioni di classifica e circuito modificabili dalla dirigenza (una sola riga, id=1)."""
    __tablename__ = "config_pickleball"

    id = Column(SmallInteger, primary_key=True, default=1)
    valori = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


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
