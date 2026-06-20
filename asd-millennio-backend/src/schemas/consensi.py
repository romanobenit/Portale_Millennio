from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConsensoCreate(BaseModel):
    socio_id: UUID
    tipo: str
    testo_versione: str
    firmato_da: UUID | None = None


class ConsensoResponse(BaseModel):
    id: UUID
    socio_id: UUID
    tipo: str
    testo_versione: str | None
    firmato_da: UUID | None
    timestamp_firma: datetime | None
    revocato_at: datetime | None

    model_config = {"from_attributes": True}
