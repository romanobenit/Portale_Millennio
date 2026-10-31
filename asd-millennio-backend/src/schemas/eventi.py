from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

SPORT_VALIDI = {"volley", "badminton", "kung_fu", "pickleball"}


def _valida_sport(v: list[str]) -> list[str]:
    pulito = [s.strip().lower() for s in v if s and s.strip()]
    if not pulito:
        raise ValueError("Indica almeno uno sport")
    for s in pulito:
        if s not in SPORT_VALIDI:
            raise ValueError(f"Sport non valido: {s}")
    return pulito


# ─── Dirigenza: input ───────────────────────────────────────────────────────

class EventoCreate(BaseModel):
    titolo: str | None = Field(None, max_length=120)
    sport: list[str]
    data: date
    ora_inizio: time
    ora_fine: time
    prezzo_eur: Decimal = Field(..., ge=0, max_digits=8, decimal_places=2)
    posti_max: int = Field(..., ge=1, le=500)
    note: str | None = None

    valida_sport = field_validator("sport")(_valida_sport)

    @model_validator(mode="after")
    def orario_valido(self):
        if self.ora_fine <= self.ora_inizio:
            raise ValueError("L'ora di fine deve essere successiva all'ora di inizio")
        return self


class EventoUpdate(BaseModel):
    titolo: str | None = Field(None, max_length=120)
    sport: list[str] | None = None
    data: date | None = None
    ora_inizio: time | None = None
    ora_fine: time | None = None
    prezzo_eur: Decimal | None = Field(None, ge=0, max_digits=8, decimal_places=2)
    posti_max: int | None = Field(None, ge=1, le=500)
    note: str | None = None

    @field_validator("sport")
    @classmethod
    def sport_validi(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else _valida_sport(v)


class PresenzeManualiUpdate(BaseModel):
    presenze_manuali: int = Field(..., ge=0, le=500)


class SegnaPresenzaRequest(BaseModel):
    presenza: Literal["presente", "assente"] | None = None
    pagato_in_sede: bool | None = None


class AggiungiPartecipanteRequest(BaseModel):
    socio_id: UUID


# ─── Socio: input ───────────────────────────────────────────────────────────

class PrenotaEventoRequest(BaseModel):
    modalita: Literal["online", "in_sede"]
    usa_credito: bool = False          # solo online: paga col credito interno invece che con Stripe


class AnnullaPrenotazioneRequest(BaseModel):
    # Per gli ingressi pagati con carta: rimborso sulla carta (Stripe) o in credito interno.
    # Gli ingressi pagati col credito tornano sempre in credito.
    rimborso: Literal["carta", "credito"] = "carta"


# ─── Output ─────────────────────────────────────────────────────────────────

class EventoPubblicoResponse(BaseModel):
    id: UUID
    titolo: str | None
    sport: list[str]
    data: date
    ora_inizio: time
    ora_fine: time
    prezzo_eur: Decimal
    posti_max: int
    partecipanti: int          # prenotazioni confermate + correzione manuale
    posti_liberi: int          # tiene conto anche dei posti trattenuti nei checkout in corso
    in_lista_attesa: int
    completo: bool
    stato: str
    # Percorso dell'immagine sotto /api/v1 (None = nessuna locandina)
    locandina_url: str | None = None


class PrenotazioneEventoResponse(BaseModel):
    id: UUID
    evento_id: UUID
    modalita: str
    stato: str
    importo_eur: Decimal
    pagato_in_sede: bool
    pagato_con_credito: bool = False
    presenza: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MiaPrenotazioneEventoResponse(PrenotazioneEventoResponse):
    evento: EventoPubblicoResponse
    annullabile: bool


class MieiEventiResponse(BaseModel):
    prenotazioni: list[MiaPrenotazioneEventoResponse]
    lista_attesa: list[UUID]
    assenze: int
    solo_online: bool          # True dopo 2 assenze "pago in sede"
    # Fino a quando può usare i campi (tessera Millennio o tessera esterna con
    # iscrizione community); None = non abilitato.
    abilitato_fino_al: date | None
    saldo_credito_eur: Decimal = Decimal("0.00")


class PrenotaEventoResponse(BaseModel):
    prenotazione: PrenotazioneEventoResponse
    stripe_checkout_url: str | None = None


class PartecipanteResponse(BaseModel):
    prenotazione_id: UUID
    socio_id: UUID
    nome: str
    cognome: str
    modalita: str
    stato: str
    importo_eur: Decimal
    pagato_in_sede: bool
    presenza: str | None
    inserita_da_staff: bool
    assenze: int
    solo_online: bool


class InAttesaResponse(BaseModel):
    socio_id: UUID
    nome: str
    cognome: str
    iscritto_at: datetime
    notificato_at: datetime | None


class EventoDirigenzaResponse(EventoPubblicoResponse):
    presenze_manuali: int
    confermati_online: int
    confermati_in_sede: int
    note: str | None


class EventoDettaglioResponse(BaseModel):
    evento: EventoDirigenzaResponse
    partecipanti: list[PartecipanteResponse]
    lista_attesa: list[InAttesaResponse]


class SocioRicercaResponse(BaseModel):
    id: UUID
    nome: str
    cognome: str
    codice_fiscale: str
    abilitato_fino_al: date | None
    assenze: int
    solo_online: bool
