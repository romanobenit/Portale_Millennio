from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

Formato = Literal["singolo", "doppio"]
Livello = Literal["sociale", "open", "federale"]
PiazzamentoTipo = Literal["vincitore", "finalista", "semifinalista", "fase_finale", "partecipazione", "nessuno"]


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
    """Le squadre possono contenere soci o ospiti (gli id di entrambi vengono riconosciuti)."""
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
    socio_id: UUID | None = None
    ospite_id: UUID | None = None
    ospite: bool = False
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
    torneo_id: UUID | None = None
    categoria: str | None = None
    fase: str | None = None
    walkover: bool = False
    fuori_classifica: str | None = None   # "walkover" | "limite amichevoli": confermata ma non conta nell'Elo
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
    inattivo: bool = False


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
    socio_id: UUID                # per gli ospiti (solo ricerca dirigenza) è l'id dell'ospite
    ospite: bool = False
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


# ─── Tornei, ospiti, circuito ───────────────────────────────────────────────

class TorneoCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=120)
    data: date
    luogo: str | None = Field(None, max_length=120)
    livello: Livello = "sociale"
    url_esterno: str | None = Field(None, max_length=500)
    note: str | None = Field(None, max_length=1000)


class TorneoUpdate(BaseModel):
    nome: str | None = Field(None, min_length=3, max_length=120)
    data: date | None = None
    luogo: str | None = Field(None, max_length=120)
    livello: Livello | None = None
    url_esterno: str | None = Field(None, max_length=500)
    note: str | None = Field(None, max_length=1000)
    concluso: bool | None = None


class TorneoResponse(BaseModel):
    id: UUID
    nome: str
    data: date
    luogo: str | None
    livello: str
    anno_sportivo: str
    concluso: bool
    url_esterno: str | None
    note: str | None
    partite: int = 0
    categorie: list[str] = []


class PiazzamentoResponse(BaseModel):
    giocatore_id: UUID
    nome: str
    ospite: bool
    categoria: str
    piazzamento: str
    punti: float
    manuale: bool


class TorneoDettaglioResponse(BaseModel):
    torneo: TorneoResponse
    partite: list[PartitaResponse]
    piazzamenti: list[PiazzamentoResponse]


class PiazzamentoUpdate(BaseModel):
    categoria: str = Field(..., min_length=1, max_length=20)
    giocatore_id: UUID
    piazzamento: PiazzamentoTipo      # "nessuno" = nessun punto (es. ritirato): i ricalcoli non lo cambiano


class GiocatoreImport(BaseModel):
    nome: str
    tipo: Literal["socio", "ospite", "nuovo_ospite"]


class RigaImportRisultato(BaseModel):
    riga: int
    categoria: str
    fase: str
    squadra_a: list[GiocatoreImport]
    squadra_b: list[GiocatoreImport]
    punteggio: str
    vincitore: str | None
    walkover: bool
    esito: Literal["ok", "errore", "saltata", "gia_importata"]
    messaggio: str | None = None


class ImportRisultatiResponse(BaseModel):
    righe: list[RigaImportRisultato]
    da_importare: int
    errori: int
    saltate: int
    gia_importate: int
    nuovi_ospiti: list[str]
    importate: int = 0          # valorizzato solo con conferma


class OspiteCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=60)
    cognome: str = Field(..., min_length=1, max_length=60)
    club: str | None = Field(None, max_length=120)
    email: EmailStr | None = None
    sesso: Literal["M", "F"] | None = None
    anno_nascita: int | None = Field(None, ge=1920, le=2025)


class OspiteUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=60)
    cognome: str | None = Field(None, min_length=1, max_length=60)
    club: str | None = Field(None, max_length=120)
    email: EmailStr | None = None
    sesso: Literal["M", "F"] | None = None
    anno_nascita: int | None = Field(None, ge=1920, le=2025)


class OspiteResponse(BaseModel):
    id: UUID
    nome: str
    cognome: str
    club: str | None
    email: str | None
    sesso: str | None
    anno_nascita: int | None
    invitato_at: datetime | None
    partite: int
    rating_singolo: float | None
    rating_doppio: float | None


class CollegaOspiteRequest(BaseModel):
    socio_id: UUID


class PuntiPiazzamento(BaseModel):
    vincitore: int = Field(..., ge=0, le=1000)
    finalista: int = Field(..., ge=0, le=1000)
    semifinalista: int = Field(..., ge=0, le=1000)
    fase_finale: int = Field(..., ge=0, le=1000)
    partecipazione: int = Field(..., ge=0, le=1000)


class MoltiplicatoriLivello(BaseModel):
    sociale: float = Field(..., ge=0.1, le=5)
    open: float = Field(..., ge=0.1, le=5)
    federale: float = Field(..., ge=0.1, le=5)


class ConfigPickleballSchema(BaseModel):
    peso_torneo: float = Field(..., ge=1, le=3)
    amichevoli_max_settimana: int = Field(..., ge=1, le=20)
    giorni_inattivita: int = Field(..., ge=14, le=730)
    migliori_risultati: int = Field(..., ge=1, le=30)
    punti: PuntiPiazzamento
    livelli: MoltiplicatoriLivello


class RisultatoCircuito(BaseModel):
    torneo_id: UUID
    torneo: str
    data: date
    piazzamento: str
    punti: float
    conta: bool                  # rientra tra i migliori risultati della stagione


class RigaCircuito(BaseModel):
    posizione: int
    giocatore_id: UUID
    nome: str
    ospite: bool = False
    punti: float
    tornei: int
    risultati: list[RisultatoCircuito]


class CircuitoResponse(BaseModel):
    anno_sportivo: str | None
    categoria: str | None
    anni: list[str]
    categorie: list[str]
    migliori_risultati: int
    righe: list[RigaCircuito]
