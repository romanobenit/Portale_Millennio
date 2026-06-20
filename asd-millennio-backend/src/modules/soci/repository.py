from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.socio import Socio
from models.tessera import Tessera
from schemas.soci import SocioCreate, SocioUpdate


class SociRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, socio_id: UUID) -> Socio | None:
        result = await self.db.execute(select(Socio).where(Socio.id == socio_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Socio | None:
        result = await self.db.execute(select(Socio).where(Socio.email == email))
        return result.scalar_one_or_none()

    async def get_by_cf(self, cf: str) -> Socio | None:
        result = await self.db.execute(
            select(Socio).where(Socio.codice_fiscale == cf.upper())
        )
        return result.scalar_one_or_none()

    async def get_by_keycloak_id(self, kc_id: str) -> Socio | None:
        result = await self.db.execute(
            select(Socio).where(Socio.keycloak_user_id == kc_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, page: int, limit: int) -> tuple[list[Socio], int]:
        offset = (page - 1) * limit
        result = await self.db.execute(select(Socio).offset(offset).limit(limit))
        total_result = await self.db.execute(select(func.count()).select_from(Socio))
        return list(result.scalars().all()), total_result.scalar_one()

    async def create(self, data: SocioCreate) -> Socio:
        socio = Socio(**data.model_dump())
        self.db.add(socio)
        await self.db.flush()
        await self.db.refresh(socio)
        return socio

    async def update(self, socio: Socio, data: SocioUpdate) -> Socio:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(socio, field, value)
        await self.db.flush()
        await self.db.refresh(socio)
        return socio

    async def get_tessera_attiva(self, socio_id: UUID, sport: str | None = None) -> Tessera | None:
        q = select(Tessera).where(
            Tessera.socio_id == socio_id,
            Tessera.stato == "attiva",
        )
        if sport:
            q = q.where(Tessera.sport == sport)
        result = await self.db.execute(q)
        return result.scalars().first()
