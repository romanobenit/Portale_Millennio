from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

Formato = Literal["singolo", "doppio"]


class PartitaCreate(BaseModel):
    """Partita inserita da un socio: lui è sempre nella squadra A."""
    formato: Formato
    data: date
    compagno_id: UUID | None = None          # solo doppio
    avversari_ids: list[UUID] = Field(..., min_length=1, max_length=2)
    punteggi: list[list[int]]                # dal punto di vista della squadra A

    @model_validator(mode="after")
    def coerenza_formato(self):
        n = 1 if self.formato == "singolo" else 2
        if len(self.avversari_ids) != n:
            raise ValueError("Numero di avversari non coerente con il formato")
        if (self.formato == "doppio") != (self.compagno_id is not None):
            raise ValueError("Il compagno si indica solo nel doppio")
        return self


class PartitaDirigenzaCreate(BaseModel):
    formato: Formato
    data: date
    squadra_a: list[UUID] = Field(..., min_length=1, max_length=2)
    squadra_b: list[UUID] = Field(..., min_length=1, max_length=2)
    punteggi: list[list[int]]
    torneo: str | None = Field(None, max_length=120)
    note: str | None = None

    @model_validator(mode="after")
    def coerenza_formato(self):
        n = 1 if self.formato == "singolo" else 2
        if len(self.squadra_a) != n or len(self.squadra_b) != n:
            raise ValueError("Numero di giocatori non coerente con il formato")
        return self


class ContestaRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=300)


class ProfiloAtletaUpdate(BaseModel):
    visibile_in_classifica: bool | None = None
    obiettivo_singolo: int | None = Field(None, ge=800, le=2500)
    obiettivo_doppio: int | None = Field(None, ge=800, le=2500)
    obiettivo_partite_mese: int | None = Field(None, ge=1, le=60)
    dupr_id: str | None = Field(None, max_length=20)
    dupr_singolo: float | None = Field(None, ge=1, le=8.5)
    dupr_doppio: float | None = Field(None, ge=1, le=8.5)


class GiocatoreBreve(BaseModel):
    socio_id: UUID
    nome: str                     # "Mario R." per i soci, nome completo per la dirigenza
    squadra: str
    rating_prima: float | None = None
    rating_dopo: float | None = None


class PartitaResponse(BaseModel):
    id: UUID
    formato: str
    data: date
    punteggi: list[list[int]]
    vincitore: str
    stato: str
    torneo: str | None
    inserita_da_dirigenza: bool
    note: str | None
    giocatori: list[GiocatoreBreve]
    created_at: datetime
    # per il socio che guarda: può confermarla/contestarla?
    da_confermare: bool = False


class RigaClassifica(BaseModel):
    posizione: int
    socio_id: UUID
    nome: str
    rating: float
    rating_max: float
    partite: int
    vittorie: int
    provvisorio: bool
    dupr: float | None = None


class PuntoAndamento(BaseModel):
    data: date
    rating: float


class StatisticheFormato(BaseModel):
    formato: str
    rating: float | None
    rating_max: float | None
    posizione: int | None
    partite: int
    vittorie: int
    provvisorio: bool
    obiettivo: int | None
    andamento: list[PuntoAndamento]


class ProfiloAtletaResponse(BaseModel):
    visibile_in_classifica: bool
    obiettivo_singolo: int | None
    obiettivo_doppio: int | None
    obiettivo_partite_mese: int | None
    dupr_id: str | None
    dupr_singolo: float | None
    dupr_doppio: float | None


class MioPickleballResponse(BaseModel):
    profilo: ProfiloAtletaResponse
    singolo: StatisticheFormato
    doppio: StatisticheFormato
    partite_questo_mese: int
    serie_vittorie: int
    compagno_frequente: str | None
    avversario_frequente: str | None
    da_confermare: list[PartitaResponse]
    in_attesa_altri: list[PartitaResponse]
    recenti: list[PartitaResponse]


class GiocatoreRicerca(BaseModel):
    socio_id: UUID
    nome: str
    rating_singolo: float | None
    rating_doppio: float | None


class SettimanaPartite(BaseModel):
    settimana: date
    partite: int


class DashboardPickleballDirigenza(BaseModel):
    giocatori_attivi_30gg: int
    partite_30gg: int
    partite_totali: int
    da_risolvere: int            # contestate
    in_attesa_conferma: int
    per_settimana: list[SettimanaPartite]
    top_singolo: list[RigaClassifica]
    top_doppio: list[RigaClassifica]
