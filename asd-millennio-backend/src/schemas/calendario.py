from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel


class SlotResponse(BaseModel):
    id: UUID
    data: date
    fascia: str
    ora_inizio: time
    ora_fine: time
    ore_totali: int
    ore_vendute: list[int]
    ore_in_lock: list[int]
    stato: str
    nft_token_id: int | None
    bloccato_fino_a: datetime | None

    model_config = {"from_attributes": True}


class DisponibilitaFascia(BaseModel):
    slot_id: UUID
    data: date
    fascia: str
    ora_inizio: time
    ora_fine: time
    ore_totali: int
    ore_vendute: list[int]
    ore_in_lock: list[int]
    ore_libere: list[int]
    stato: str
    prezzo_ora: float
    moltiplicatore_data: float
    moltiplicatore_scarsita: float
    sconto_promo_pct: float


class OreSelezione(BaseModel):
    slot_id: UUID
    ore: list[int]


class LockRequest(BaseModel):
    selezione: list[OreSelezione]


class DettaglioSlot(BaseModel):
    slot_id: str
    fascia: str
    data: str
    ore_selezionate: list[int]
    n_ore: int
    tariffa_base: float
    moltiplicatore_data: float
    moltiplicatore_scarsita: float
    sconto_promo_pct: float
    prezzo_ora: float
    costo_slot: float


class RiepilogoSelezione(BaseModel):
    selezione: list[dict]
    ore_notte: int
    ore_mattina: int
    ore_pomeriggio: int
    costo_totale: float
    dettaglio: list[DettaglioSlot] = []
