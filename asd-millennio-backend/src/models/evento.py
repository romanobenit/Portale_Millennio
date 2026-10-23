import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from core.database import Base

StatoEvento = Enum("programmato", "annullato", name="stato_evento")
ModalitaPrenotazioneEvento = Enum("online", "in_sede", name="modalita_prenotazione_evento")
StatoPrenotazioneEvento = Enum(
    "in_attesa_pagamento",
    "confermata",
    "annullata",
    "scaduta",
    "rimborsata",
    name="stato_prenotazione_evento",
)
PresenzaEvento = Enum("presente", "assente", name="presenza_evento")


class EventoCampo(Base):
    """
    Finestra di utilizzo del Palasirio (tipicamente 1h30–2h) individuata dalla dirigenza.
    L'ingresso vale per tutta la durata: niente prenotazione per ora.
    """
    __tablename__ = "eventi_campo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titolo = Column(String, nullable=True)
    sport = Column(ARRAY(String), nullable=False, default=list)
    data = Column(Date, nullable=False, index=True)
    ora_inizio = Column(Time, nullable=False)
    ora_fine = Column(Time, nullable=False)
    prezzo_eur = Column(Numeric(8, 2), nullable=False)
    posti_max = Column(SmallInteger, nullable=False)
    # Correzione manuale del contatore (es. chi entra senza aver prenotato).
    presenze_manuali = Column(SmallInteger, nullable=False, default=0)
    stato = Column(StatoEvento, nullable=False, default="programmato")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    prenotazioni = relationship("PrenotazioneEvento", back_populates="evento")


class PrenotazioneEvento(Base):
    __tablename__ = "prenotazioni_evento"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evento_id = Column(UUID(as_uuid=True), ForeignKey("eventi_campo.id"), nullable=False, index=True)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    modalita = Column(ModalitaPrenotazioneEvento, nullable=False)
    stato = Column(StatoPrenotazioneEvento, nullable=False)
    importo_eur = Column(Numeric(8, 2), nullable=False)
    pagato_in_sede = Column(Boolean, nullable=False, default=False)
    presenza = Column(PresenzaEvento, nullable=True)
    presenza_segnata_at = Column(DateTime(timezone=True), nullable=True)
    inserita_da_staff = Column(Boolean, nullable=False, default=False)
    stripe_session_id = Column(String, unique=True, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True, index=True)
    # Posto trattenuto durante il checkout Stripe; oltre questa soglia si libera.
    bloccata_fino_a = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    evento = relationship("EventoCampo", back_populates="prenotazioni")
    socio = relationship("Socio")


class ListaAttesaEvento(Base):
    __tablename__ = "lista_attesa_evento"
    __table_args__ = (UniqueConstraint("evento_id", "socio_id", name="uq_lista_attesa_evento_socio"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evento_id = Column(UUID(as_uuid=True), ForeignKey("eventi_campo.id"), nullable=False, index=True)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), nullable=False, index=True)
    notificato_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
