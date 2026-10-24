from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MovimentoCreditoResponse(BaseModel):
    id: UUID
    tipo: str
    importo_eur: Decimal
    saldo_dopo_eur: Decimal
    causale: str | None
    prenotazione_evento_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MioCreditoResponse(BaseModel):
    saldo_eur: Decimal
    movimenti: list[MovimentoCreditoResponse]
    ricarica_online_attiva: bool
    ricarica_min_eur: int
    ricarica_max_eur: int
    saldo_max_eur: int


class RicaricaOnlineRequest(BaseModel):
    importo_eur: int = Field(..., ge=1, le=1000)


class RicaricaOnlineResponse(BaseModel):
    stripe_checkout_url: str


class MovimentoDirigenzaCreate(BaseModel):
    tipo: Literal["accredito", "storno", "ricarica_sede"]
    importo_eur: Decimal = Field(..., gt=0, le=1000, decimal_places=2)  # sempre positivo: il segno lo dà il tipo
    causale: str | None = Field(None, max_length=300)


class SaldoSocioResponse(BaseModel):
    socio_id: UUID
    nome: str
    cognome: str
    codice_fiscale: str
    saldo_eur: Decimal


class SchedaCreditoSocioResponse(SaldoSocioResponse):
    movimenti: list[MovimentoCreditoResponse]


class TotalePerTipo(BaseModel):
    tipo: str
    movimenti: int
    totale_eur: Decimal


class RiepilogoCreditoResponse(BaseModel):
    credito_in_circolo_eur: Decimal     # somma dei saldi di tutti i soci
    soci_con_saldo: int
    ultimi_30gg: list[TotalePerTipo]
    ricarica_online_attiva: bool
