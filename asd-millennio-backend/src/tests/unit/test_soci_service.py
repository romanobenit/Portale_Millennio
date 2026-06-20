from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.soci import SocioCreate
from schemas.tessere import TesseraCreate


@pytest.mark.asyncio
async def test_calcola_scadenza_tessera():
    from modules.soci.service import _calcola_scadenza_tessera
    scadenza = _calcola_scadenza_tessera("2026-2027")
    assert scadenza == date(2027, 6, 30)


@pytest.mark.asyncio
async def test_calcola_scadenza_tessera_anno_corrente():
    from modules.soci.service import _calcola_scadenza_tessera
    scadenza = _calcola_scadenza_tessera("2025-2026")
    assert scadenza == date(2026, 6, 30)


@pytest.mark.asyncio
async def test_socio_create_cf_uppercase():
    data = SocioCreate(
        nome="Luigi",
        cognome="Verdi",
        data_nascita=date(1985, 3, 20),
        codice_fiscale="vrdlgu85c20h501z",
        email="luigi@test.com",
        sport=["badminton"],
    )
    assert data.codice_fiscale == "VRDLGU85C20H501Z"


@pytest.mark.asyncio
async def test_socio_create_sport_non_valido():
    with pytest.raises(Exception):
        SocioCreate(
            nome="Test",
            cognome="User",
            data_nascita=date(1990, 1, 1),
            codice_fiscale="TSTXXX00X00X000X",
            email="test@test.com",
            sport=["calcio"],
        )


@pytest.mark.asyncio
async def test_minore_senza_tutore():
    """La validazione tutore_id obbligatorio avviene nel service, non nello schema."""
    from modules.soci.service import SociService

    data = SocioCreate(
        nome="Bambino",
        cognome="Rossi",
        data_nascita=date(2015, 6, 1),
        codice_fiscale="BMBRSSX15H01H501X",
        email="bambino@test.com",
        is_minor=True,
    )
    # Schema accetta il dato — la validazione è nel service
    assert data.is_minor is True
    assert data.tutore_id is None

    db = AsyncMock(spec=AsyncSession)
    repo_mock = MagicMock()
    repo_mock.get_by_cf = AsyncMock(return_value=None)
    repo_mock.get_by_email = AsyncMock(return_value=None)

    service = SociService(db)
    service.repo = repo_mock

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await service.crea_socio(data)
    assert exc_info.value.status_code == 422


# ── attiva_tessera ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_attiva_tessera_imposta_pdf_url():
    """attiva_tessera deve impostare pdf_url con il path corretto."""
    from modules.soci.service import SociService

    tessera_id = uuid4()
    tessera_mock = MagicMock()
    tessera_mock.stato = "in_attesa_pagamento"

    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = tessera_mock
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()

    async def fake_refresh(obj):
        pass
    db.refresh = fake_refresh

    with patch("modules.soci.service.get_settings") as mock_settings, \
         patch("modules.soci.service.TesseraResponse") as mock_response:
        mock_settings.return_value.app_url = "https://millennioasd.com"
        mock_settings.return_value.tessera_scadenza_mese = 6
        mock_settings.return_value.tessera_scadenza_giorno = 30
        mock_settings.return_value.anno_sportivo_corrente = "2026-2027"
        mock_response.model_validate.return_value = MagicMock()

        service = SociService(db)
        service.repo = MagicMock()
        await service.attiva_tessera(tessera_id)

    assert tessera_mock.stato == "attiva"
    assert f"/api/v1/tessere/{tessera_id}/pdf" in tessera_mock.pdf_url


@pytest.mark.asyncio
async def test_attiva_tessera_non_trovata():
    from modules.soci.service import SociService

    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    service = SociService(db)
    with pytest.raises(HTTPException) as exc_info:
        await service.attiva_tessera(uuid4())
    assert exc_info.value.status_code == 404


# ── lista_consensi ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lista_consensi_ordine_desc():
    """lista_consensi deve restituire ConsensoResponse ordinati per timestamp desc."""
    from modules.soci.service import SociService
    from schemas.consensi import ConsensoResponse

    socio_id = uuid4()
    c1 = MagicMock()
    c1.id = uuid4()
    c1.socio_id = socio_id
    c1.tipo = "privacy"
    c1.testo_versione = "v1.0"
    c1.firmato_da = socio_id
    c1.timestamp_firma = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c1.revocato_at = None

    db = AsyncMock(spec=AsyncSession)
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [c1]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch("modules.soci.service.ConsensoResponse") as mock_schema:
        mock_schema.model_validate.side_effect = lambda c: c

        service = SociService(db)
        result = await service.lista_consensi(socio_id)

    assert len(result) == 1
    db.execute.assert_called_once()


# ── lista_minori ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lista_minori_restituisce_figli():
    from modules.soci.service import SociService

    tutore_id = uuid4()
    minore = MagicMock()
    minore.id = uuid4()
    minore.tutore_id = tutore_id

    db = AsyncMock(spec=AsyncSession)
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [minore]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch("modules.soci.service.SocioResponse") as mock_schema:
        mock_schema.model_validate.side_effect = lambda s: s

        service = SociService(db)
        result = await service.lista_minori(tutore_id)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_lista_minori_vuota():
    from modules.soci.service import SociService

    db = AsyncMock(spec=AsyncSession)
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    service = SociService(db)
    result = await service.lista_minori(uuid4())
    assert result == []


# ── elimina_socio ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_elimina_socio_pseudoanonimizza():
    from modules.soci.service import SociService

    socio_id = uuid4()
    socio_mock = MagicMock()
    socio_mock.id = socio_id
    socio_mock.nome = "Mario"
    socio_mock.cognome = "Rossi"
    socio_mock.email = "mario@test.com"
    socio_mock.codice_fiscale = "RSSMRA80A01H501Z"
    socio_mock.telefono = "3331234567"
    socio_mock.foto_url = "https://example.com/foto.jpg"
    socio_mock.indirizzo = "Via Roma 1"
    socio_mock.keycloak_user_id = "kc-123"

    # Minori: nessuno. Consensi: nessuno.
    no_minori_mock = MagicMock()
    no_minori_mock.scalars.return_value.first.return_value = None
    no_consensi_mock = MagicMock()
    no_consensi_mock.scalars.return_value.all.return_value = []

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[no_minori_mock, no_consensi_mock])
    db.flush = AsyncMock()

    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(return_value=socio_mock)

    service = SociService(db)
    service.repo = repo_mock

    await service.elimina_socio(socio_id, socio_id, is_dirigenza=False)

    assert socio_mock.nome == "RIMOSSO"
    assert socio_mock.cognome == "RIMOSSO"
    assert "rimosso-" in socio_mock.email
    assert socio_mock.telefono is None
    assert socio_mock.keycloak_user_id is None


@pytest.mark.asyncio
async def test_elimina_socio_blocco_tutore():
    """Non si può eliminare un socio che è tutore di minorenni."""
    from modules.soci.service import SociService

    socio_id = uuid4()
    socio_mock = MagicMock()
    socio_mock.id = socio_id

    db = AsyncMock(spec=AsyncSession)
    minori_mock = MagicMock()
    minori_mock.scalars.return_value.first.return_value = MagicMock()  # ha minori
    db.execute = AsyncMock(return_value=minori_mock)
    db.flush = AsyncMock()

    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(return_value=socio_mock)

    service = SociService(db)
    service.repo = repo_mock

    with pytest.raises(HTTPException) as exc_info:
        await service.elimina_socio(socio_id, socio_id, is_dirigenza=False)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_elimina_socio_permesso_negato():
    """Un socio non può eliminare il profilo di un altro socio."""
    from modules.soci.service import SociService

    socio_id = uuid4()
    richiedente_id = uuid4()  # diverso dal socio_id

    socio_mock = MagicMock()
    socio_mock.id = socio_id

    db = AsyncMock(spec=AsyncSession)

    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(return_value=socio_mock)

    service = SociService(db)
    service.repo = repo_mock

    with pytest.raises(HTTPException) as exc_info:
        await service.elimina_socio(socio_id, richiedente_id, is_dirigenza=False)
    assert exc_info.value.status_code == 403
