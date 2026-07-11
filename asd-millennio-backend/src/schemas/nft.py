from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OreSelezioneNFT(BaseModel):
    slot_id: UUID
    ore: list[int]


class AcquistoNFTRequest(BaseModel):
    selezione: list[OreSelezioneNFT]
    acquisto_per_minore: bool = False
    minore_id: UUID | None = None


class AcquistoNFTResponse(BaseModel):
    id: UUID
    stripe_session_id: str
    stripe_checkout_url: str
    importo_eur: float
    slot_count: int


class AcquistoNFTDetail(BaseModel):
    id: UUID
    token_id: int | None
    ipfs_uri: str | None
    importo_eur: float
    stato: str
    wallet_address: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MioNFTResponse(BaseModel):
    """Voce della pagina soci "I miei NFT"."""
    id: UUID
    token_id: int | None
    contract_address: str | None
    mint_tx_hash: str | None
    ipfs_uri: str | None
    importo_eur: float
    ore_totali: int
    stato: str
    data_primo_slot: str | None
    polygonscan_url: str | None
    certificato_disponibile: bool
    created_at: datetime


class NFTVerificaResponse(BaseModel):
    valid: bool
    socio: str | None
    slot: dict | None
    checked_at: datetime


class DashboardFundraisingResponse(BaseModel):
    totale_raccolto_eur: float
    obiettivo_eur: float
    percentuale: float
    nft_emessi_totali: int
    nft_per_fascia: dict[str, int]
