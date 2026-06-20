import asyncio
import uuid
from datetime import date
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import Base, get_db
from main import app

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/millennio_test"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine_test, expire_on_commit=False)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(setup_db) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def socio_data() -> dict:
    cf = f"TSTMLN{uuid.uuid4().hex[:9].upper()}"[:16]
    return {
        "nome": "Mario",
        "cognome": "Rossi",
        "data_nascita": "1990-01-15",
        "codice_fiscale": cf,
        "email": f"mario.{uuid.uuid4().hex[:6]}@test.com",
        "telefono": "3331234567",
        "is_minor": False,
        "sport": ["volley"],
    }


def mock_jwt_user(sub: str = "test-keycloak-id", roles: list[str] | None = None) -> dict:
    return {
        "sub": sub,
        "email": "staff@millennioasd.com",
        "realm_access": {"roles": roles or ["staff"]},
    }
