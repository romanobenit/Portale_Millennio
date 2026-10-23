from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class SocioOnboarding(BaseModel):
    """Auto-creazione del profilo adulto al primo accesso (POST /soci/me)."""
    nome: str
    cognome: str
    data_nascita: date
    codice_fiscale: str
    indirizzo: str | None = None
    telefono: str | None = None
    # email non richiesta: si usa quella del token Keycloak

    @field_validator("codice_fiscale")
    @classmethod
    def cf_up(cls, v: str) -> str:
        return v.upper().strip()


class MinoreCreate(BaseModel):
    """Il tutore aggiunge un figlio minorenne (POST /soci/me/minori)."""
    nome: str
    cognome: str
    data_nascita: date
    codice_fiscale: str
    indirizzo: str | None = None

    @field_validator("codice_fiscale")
    @classmethod
    def cf_up(cls, v: str) -> str:
        return v.upper().strip()


class DocumentoResponse(BaseModel):
    id: UUID
    tipo: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TesseramentoRequest(BaseModel):
    """Avvio del tesseramento per una categoria (POST /soci/me/tesseramento)."""
    categoria: str  # 'volley','badminton','kung_fu','pickleball','sostenitore'

    @field_validator("categoria")
    @classmethod
    def cat_valida(cls, v: str) -> str:
        validi = {"volley", "badminton", "kung_fu", "pickleball", "sostenitore", "community"}
        if v not in validi:
            raise ValueError(f"Categoria non valida: {v}")
        return v


class TesseramentoCheckoutResponse(BaseModel):
    tessera_id: UUID
    pagamento_id: UUID
    stripe_checkout_url: str
    importo_eur: float


class TesseraEsternaCreate(BaseModel):
    ente: str = Field(..., min_length=2, max_length=120)
    asd_nome: str = Field(..., min_length=2, max_length=160)
    asd_codice: str | None = Field(None, max_length=40)
    numero_tessera: str = Field(..., min_length=1, max_length=60)
    disciplina: str = Field(..., min_length=2, max_length=60)
    data_scadenza: date

    @field_validator("ente", "asd_nome", "numero_tessera", "disciplina", "asd_codice")
    @classmethod
    def ripulisci(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class AnagraficaInSede(BaseModel):
    nome: str = Field(..., min_length=1, max_length=80)
    cognome: str = Field(..., min_length=1, max_length=80)
    data_nascita: date
    codice_fiscale: str
    email: EmailStr
    telefono: str | None = None
    indirizzo: str | None = None

    @field_validator("codice_fiscale")
    @classmethod
    def cf_up(cls, v: str) -> str:
        return v.upper().strip()


class TesseramentoInSedeRequest(BaseModel):
    """
    Tesseramento fatto dalla dirigenza in sede (POST /soci/tesseramento-in-sede):
    quota pagata in sede, documento visto di persona → tessera attiva e già verificata.
    Indicare `socio_id` (socio già registrato) oppure `anagrafica` (nuovo socio).
    """
    socio_id: UUID | None = None
    anagrafica: AnagraficaInSede | None = None
    categoria: str
    consensi_firmati: bool

    @field_validator("categoria")
    @classmethod
    def cat_valida(cls, v: str) -> str:
        if v not in {"volley", "badminton", "kung_fu", "pickleball", "sostenitore"}:
            raise ValueError(f"Categoria non valida: {v}")
        return v

    @model_validator(mode="after")
    def socio_o_anagrafica(self):
        if (self.socio_id is None) == (self.anagrafica is None):
            raise ValueError("Indica un socio esistente oppure i dati di un nuovo socio")
        return self


class TesseramentoInSedeResponse(BaseModel):
    socio_id: UUID
    nome: str
    cognome: str
    tessera_id: UUID
    numero_tessera: str
    categoria: str
    data_scadenza: date | None


# ── verifica staff ────────────────────────────────────────────────────────────

class DocumentoBreve(BaseModel):
    id: UUID
    tipo: str
    filename: str


class SocioBreve(BaseModel):
    id: UUID
    nome: str
    cognome: str
    codice_fiscale: str
    is_minor: bool


class TesseraEsternaResponse(BaseModel):
    id: UUID
    socio_id: UUID
    ente: str
    asd_nome: str
    asd_codice: str | None
    numero_tessera: str
    disciplina: str
    data_scadenza: date
    documento_id: UUID | None
    verifica_stato: str
    verifica_scadenza: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TesseramentoDaVerificare(BaseModel):
    # "tesseramento" = nuova tessera (anche community); "rinnovo_tessera_esterna" =
    # tessera esterna aggiornata da un iscritto community già confermato.
    tipo: str = "tesseramento"
    tessera_id: UUID
    numero_tessera: str
    categoria: str
    anno_sportivo: str | None
    verifica_scadenza: datetime | None
    importo_eur: float | None
    socio: SocioBreve
    tutore: SocioBreve | None
    documenti: list[DocumentoBreve]
    tessera_esterna: TesseraEsternaResponse | None = None


class TesseratoResponse(BaseModel):
    """Riga della lista completa dei tesserati (tutte le tessere, non solo quelle in verifica)."""
    tessera_id: UUID
    numero_tessera: str
    categoria: str
    stato: str
    anno_sportivo: str | None
    data_scadenza: date | None
    verifica_stato: str | None
    certificato_medico_tipo: str | None
    certificato_medico_scadenza: date | None
    tessera_esterna_scadenza: date | None = None
    socio: SocioBreve
    tutore: SocioBreve | None


class CertificatoMedicoResponse(BaseModel):
    tessera_id: UUID
    certificato_medico_tipo: str
    certificato_medico_scadenza: date


# ── quote (dirigenza) ─────────────────────────────────────────────────────────

class QuotaCreate(BaseModel):
    categoria: str
    is_minore: bool = False
    importo_eur: float
    anno_sportivo: str
    note: str | None = None

    @field_validator("categoria")
    @classmethod
    def cat_valida(cls, v: str) -> str:
        validi = {"volley", "badminton", "kung_fu", "pickleball", "sostenitore", "community"}
        if v not in validi:
            raise ValueError(f"Categoria non valida: {v}")
        return v


class QuotaUpdate(BaseModel):
    importo_eur: float | None = None
    attivo: bool | None = None
    note: str | None = None


class QuotaResponse(BaseModel):
    id: UUID
    categoria: str
    is_minore: bool
    importo_eur: float
    anno_sportivo: str
    attivo: bool
    note: str | None

    model_config = {"from_attributes": True}
