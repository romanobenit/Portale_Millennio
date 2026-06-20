from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

SPORT_PREFISSI = {
    "volley": "VOL",
    "badminton": "BDM",
    "kung_fu": "KFU",
    "pickleball": "PCK",
}


class TesseraCreate(BaseModel):
    socio_id: UUID | None = None   # iniettato dal path nel router POST /{socio_id}/tessere
    sport: str
    anno_sportivo: str | None = None


class TesseraResponse(BaseModel):
    id: UUID
    socio_id: UUID
    numero_tessera: str
    sport: str
    stato: str
    data_emissione: date | None
    data_scadenza: date | None
    anno_sportivo: str | None
    pdf_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TesseraVerificaResponse(BaseModel):
    valida: bool
    numero_tessera: str
    sport: str
    stato: str
    data_scadenza: date | None
    socio_nome: str
    socio_cognome: str
