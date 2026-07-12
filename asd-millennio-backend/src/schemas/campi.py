from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Template (dirigenza) ───────────────────────────────────────────────────

class SlotTemplateCampoCreate(BaseModel):
    giorno_settimana: int = Field(..., ge=0, le=6, description="0=Lunedì, 6=Domenica")
    ora_inizio: time
    ora_fine: time
    num_campi: int = Field(4, ge=1, le=20)
    costo_ora: Decimal = Field(..., gt=0)
    sport: List[str] = Field(default_factory=list)
    attivo: bool = True
    valido_dal: date
    valido_fino_al: date
    note: Optional[str] = None


class SlotTemplateCampoUpdate(BaseModel):
    giorno_settimana: Optional[int] = Field(None, ge=0, le=6)
    ora_inizio: Optional[time] = None
    ora_fine: Optional[time] = None
    num_campi: Optional[int] = Field(None, ge=1, le=20)
    costo_ora: Optional[Decimal] = Field(None, gt=0)
    sport: Optional[List[str]] = None
    attivo: Optional[bool] = None
    valido_dal: Optional[date] = None
    valido_fino_al: Optional[date] = None
    note: Optional[str] = None


class SlotTemplateCampoResponse(BaseModel):
    id: UUID
    giorno_settimana: int
    ora_inizio: time
    ora_fine: time
    num_campi: int
    costo_ora: Decimal
    sport: List[str]
    attivo: bool
    valido_dal: date
    valido_fino_al: date
    note: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Disponibilità ──────────────────────────────────────────────────────────

class GiornoDisponibileResponse(BaseModel):
    """Rappresenta una singola fascia oraria in un giorno specifico."""
    data: date
    template_id: UUID
    giorno_settimana: int
    ora_inizio: time
    ora_fine: time
    campi_totali: int
    campi_disponibili: int
    costo_ora: Decimal
    durata_ore: int
    importo_totale: Decimal
    sport: List[str]


# ─── Prenotazione (socio) ───────────────────────────────────────────────────

class PrenotazioneCampoCreate(BaseModel):
    template_id: UUID
    data: date
    ora_inizio: time  # inizio dello slot da 1 ora scelto (HH:MM)


class PrenotazioneCampoResponse(BaseModel):
    id: UUID
    socio_id: UUID
    template_id: UUID
    data: date
    ora_inizio: time
    ora_fine: time
    campo: int
    importo_eur: Decimal
    stato: str
    stripe_session_id: Optional[str]
    bloccata_fino_a: Optional[datetime]
    cancellabile_fino_a: Optional[datetime]
    note: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckoutCampoResponse(BaseModel):
    prenotazione_id: UUID
    stripe_checkout_url: str
    campo: int
    importo_eur: Decimal
    bloccata_fino_a: datetime


class CheckoutCarrelloResponse(BaseModel):
    """Pagamento unico di tutto il carrello (più ore/campi in una sola sessione Stripe)."""
    stripe_checkout_url: str
    importo_totale: Decimal
    num_slot: int


class CancellazioneCampoResponse(BaseModel):
    prenotazione_id: UUID
    messaggio: str
