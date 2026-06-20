from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class SocioCreate(BaseModel):
    nome: str
    cognome: str
    data_nascita: date
    codice_fiscale: str
    indirizzo: str | None = None
    email: EmailStr
    telefono: str | None = None
    is_minor: bool = False
    tutore_id: UUID | None = None
    sport: list[str] = []

    @field_validator("codice_fiscale")
    @classmethod
    def cf_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("sport")
    @classmethod
    def sport_validi(cls, v: list[str]) -> list[str]:
        validi = {"volley", "badminton", "kung_fu", "pickleball"}
        for s in v:
            if s not in validi:
                raise ValueError(f"Sport non valido: {s}")
        return v


class SocioUpdate(BaseModel):
    nome: str | None = None
    cognome: str | None = None
    indirizzo: str | None = None
    telefono: str | None = None
    foto_url: str | None = None
    sport: list[str] | None = None


class SocioResponse(BaseModel):
    id: UUID
    nome: str
    cognome: str
    data_nascita: date
    codice_fiscale: str
    indirizzo: str | None
    email: str
    telefono: str | None
    foto_url: str | None
    is_minor: bool
    tutore_id: UUID | None
    sport: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SocioListResponse(BaseModel):
    items: list[SocioResponse]
    total: int
    page: int
    limit: int
