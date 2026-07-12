from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


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
        validi = {"volley", "badminton", "kung_fu", "pickleball", "sostenitore"}
        if v not in validi:
            raise ValueError(f"Categoria non valida: {v}")
        return v


class TesseramentoCheckoutResponse(BaseModel):
    tessera_id: UUID
    pagamento_id: UUID
    stripe_checkout_url: str
    importo_eur: float


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


class TesseramentoDaVerificare(BaseModel):
    tessera_id: UUID
    numero_tessera: str
    categoria: str
    anno_sportivo: str | None
    verifica_scadenza: datetime | None
    importo_eur: float | None
    socio: SocioBreve
    tutore: SocioBreve | None
    documenti: list[DocumentoBreve]


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
        validi = {"volley", "badminton", "kung_fu", "pickleball", "sostenitore"}
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
