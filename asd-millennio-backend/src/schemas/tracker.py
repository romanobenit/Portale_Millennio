from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Sport = Literal["kung_fu", "pallavolo", "badminton", "pickleball", "tornei_pickleball", "basket_serale", "calcio_a_5"]
Fonte = Literal["meta_ads", "organico", "torneo", "passaggio_struttura", "passaparola", "altro"]
Canale = Literal["whatsapp", "email", "instagram"]
Stato = Literal["lead", "prova_prenotata", "prova_svolta", "iscritto", "pagato", "perso"]
Abbonamento = Literal["mensile", "annuale"]


def _testo(v: str | None) -> str | None:
    if v is None:
        return None
    v = " ".join(v.split()) if "\n" not in v else v.strip()
    return v or None


# ─── Input ──────────────────────────────────────────────────────────────────

class ContattoCreate(BaseModel):
    data_contatto: date
    sport: Sport
    fonte: Fonte
    nome: str = Field(..., min_length=2, max_length=120)
    canale: Canale | None = None
    recapito: str | None = Field(None, max_length=120)
    stato: Stato = "lead"
    data_prova: date | None = None
    tipo_abbonamento: Abbonamento | None = None
    importo_eur: Decimal | None = Field(None, ge=0, le=100000, max_digits=10, decimal_places=2)
    responsabile_id: UUID | None = None
    prossimo_followup: date | None = None
    note: str | None = Field(None, max_length=1000)
    is_test: bool = False

    _pulisci = field_validator("nome", "recapito", "note")(_testo)


class ContattoUpdate(BaseModel):
    """Solo i campi inviati vengono modificati; null svuota i campi facoltativi."""
    data_contatto: date | None = None
    sport: Sport | None = None
    fonte: Fonte | None = None
    nome: str | None = Field(None, min_length=2, max_length=120)
    canale: Canale | None = None
    recapito: str | None = Field(None, max_length=120)
    stato: Stato | None = None
    data_prova: date | None = None
    tipo_abbonamento: Abbonamento | None = None
    importo_eur: Decimal | None = Field(None, ge=0, le=100000, max_digits=10, decimal_places=2)
    responsabile_id: UUID | None = None
    prossimo_followup: date | None = None
    note: str | None = Field(None, max_length=1000)
    is_test: bool | None = None

    _pulisci = field_validator("nome", "recapito", "note")(_testo)


class CancellaPersiRequest(BaseModel):
    fino_al: date               # contatti passati a "perso" fino a questa data compresa
    conferma: bool = False      # False = solo anteprima del numero


class CostoIstruttoreCreate(BaseModel):
    sport: Sport
    valido_dal: date            # qualsiasi giorno: viene portato al primo del mese
    costo_mensile_eur: Decimal = Field(..., ge=0, le=100000, max_digits=10, decimal_places=2)


# ─── Output ─────────────────────────────────────────────────────────────────

class MembroResponse(BaseModel):
    id: UUID
    nome: str
    ruolo: str

    model_config = {"from_attributes": True}


class MeTrackerResponse(MembroResponse):
    dirigenza: bool             # vede i riepiloghi, gestisce i costi, cancella su richiesta


class ContattoResponse(BaseModel):
    id: UUID
    data_contatto: date
    sport: str
    fonte: str
    nome: str
    canale: str | None
    recapito: str | None
    stato: str
    data_prova: date | None
    tipo_abbonamento: str | None
    importo_eur: Decimal | None
    responsabile_id: UUID | None
    responsabile_nome: str | None
    prossimo_followup: date | None
    note: str | None
    is_test: bool
    created_at: datetime
    updated_at: datetime


class CambioStatoResponse(BaseModel):
    stato: str
    cambiato_at: datetime
    cambiato_da: str | None


class ContattoDettaglioResponse(ContattoResponse):
    storico: list[CambioStatoResponse]


class ListaContattiResponse(BaseModel):
    contatti: list[ContattoResponse]
    totale: int
    page: int
    limit: int


class RigaRiepilogo(BaseModel):
    sport: str                  # chiave della tendina; "totale" per la riga finale
    lead: int
    prove_prenotate: int
    prove_svolte: int
    iscritti: int
    paganti: int
    persi: int
    conversione_pct: Decimal | None
    incassato_eur: Decimal
    impegnato_eur: Decimal
    costo_istruttore_eur: Decimal | None    # None nella vista per fonte: il costo è per sport, non per fonte
    margine_eur: Decimal | None


class RiepilogoResponse(BaseModel):
    fonte: str | None
    dal: date | None
    al: date | None
    solo_test: bool
    righe: list[RigaRiepilogo]
    totale: RigaRiepilogo


class CancellaPersiResponse(BaseModel):
    fino_al: date
    contatti: int               # quanti sono (anteprima) o sono stati cancellati
    cancellati: bool


class CostoIstruttoreResponse(BaseModel):
    id: UUID
    sport: str
    valido_dal: date
    costo_mensile_eur: Decimal

    model_config = {"from_attributes": True}
