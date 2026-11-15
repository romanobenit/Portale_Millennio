import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

# Le tendine del brief: valori chiusi, così i conteggi tornano sempre.
SportTracker = Enum(
    "kung_fu", "pallavolo", "badminton", "pickleball", "tornei_pickleball", "basket_serale", "calcio_a_5",
    name="sport_tracker",
)
FonteContatto = Enum(
    "meta_ads", "organico", "torneo", "passaggio_struttura", "passaparola", "altro",
    name="fonte_contatto",
)
CanaleContatto = Enum("whatsapp", "email", "instagram", name="canale_contatto")
StatoContatto = Enum(
    "lead", "prova_prenotata", "prova_svolta", "iscritto", "pagato", "perso",
    name="stato_contatto",
)
TipoAbbonamentoTracker = Enum("mensile", "annuale", name="tipo_abbonamento_tracker")


class MembroTracker(Base):
    """
    Chi usa il tracker (Rita e i dirigenti): registrato al primo accesso, serve per
    la tendina "Responsabile follow-up" senza interrogare Keycloak.
    """
    __tablename__ = "membri_tracker"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keycloak_user_id = Column(String, unique=True, nullable=False)
    nome = Column(String, nullable=False)
    ruolo = Column(String, nullable=False)          # "tracker" o "dirigenza"
    ultimo_accesso = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ContattoTracker(Base):
    """
    Una persona interessata a uno sport: resta la stessa riga dal primo messaggio
    all'iscrizione (o alla perdita), cambia solo lo stato. Non si cancella, salvo
    richiesta di rimozione dell'interessato.
    """
    __tablename__ = "contatti_tracker"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_contatto = Column(Date, nullable=False, index=True)
    sport = Column(SportTracker, nullable=False, index=True)
    fonte = Column(FonteContatto, nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    canale = Column(CanaleContatto, nullable=True)
    recapito = Column(String(120), nullable=True)   # numero, email o profilo, secondo il canale
    stato = Column(StatoContatto, nullable=False, index=True)
    data_prova = Column(Date, nullable=True)
    tipo_abbonamento = Column(TipoAbbonamentoTracker, nullable=True)
    importo_eur = Column(Numeric(10, 2), nullable=True)
    responsabile_id = Column(UUID(as_uuid=True), ForeignKey("membri_tracker.id"), nullable=True, index=True)
    prossimo_followup = Column(Date, nullable=True, index=True)
    note = Column(Text, nullable=True)
    is_test = Column(Boolean, nullable=False, default=False)   # righe di prova: fuori dai conteggi reali
    creato_da_id = Column(UUID(as_uuid=True), ForeignKey("membri_tracker.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class StatoContattoStorico(Base):
    """Ogni cambio di stato: serve a contare chi ha raggiunto una fase anche se poi è andato avanti o è perso."""
    __tablename__ = "contatti_tracker_stati"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contatto_id = Column(
        UUID(as_uuid=True), ForeignKey("contatti_tracker.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stato = Column(StatoContatto, nullable=False)
    cambiato_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cambiato_da_id = Column(UUID(as_uuid=True), ForeignKey("membri_tracker.id"), nullable=True)


class CostoIstruttore(Base):
    """Costo mensile dell'istruttore per sport, valido dal mese indicato fino alla variazione successiva."""
    __tablename__ = "costi_istruttore"
    __table_args__ = (UniqueConstraint("sport", "valido_dal", name="uq_costo_istruttore_sport_mese"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sport = Column(SportTracker, nullable=False)
    valido_dal = Column(Date, nullable=False)       # sempre il primo giorno del mese
    costo_mensile_eur = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
