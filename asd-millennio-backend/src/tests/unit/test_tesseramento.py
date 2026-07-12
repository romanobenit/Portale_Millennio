"""Test onboarding self-service (Fase 2): CF, creazione profilo, conferma pagamento quota."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


# ── codice fiscale ────────────────────────────────────────────────────────────

def test_cf_valido():
    from modules.soci.codice_fiscale import cf_valido
    assert cf_valido("MRTMTT91D08F205J") is True
    assert cf_valido("mrtmtt91d08f205j") is True           # case-insensitive
    assert cf_valido("MRTMTT91D08F205A") is False           # check char errato
    assert cf_valido("ABC") is False                         # formato
    assert cf_valido("") is False


# ── crea_profilo_self: guardrail ──────────────────────────────────────────────

def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _onboarding(cf="MRTMTT91D08F205J", nascita=date(1991, 4, 8)):
    d = MagicMock()
    d.codice_fiscale = cf
    d.data_nascita = nascita
    d.nome = "Matteo"
    d.cognome = "Marotta"
    d.indirizzo = None
    d.telefono = None
    return d


@pytest.mark.asyncio
async def test_profilo_self_409_se_esiste():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    svc.repo.get_by_keycloak_id = AsyncMock(return_value=MagicMock())  # già esiste
    with pytest.raises(HTTPException) as e:
        await svc.crea_profilo_self("kc-sub", "a@b.it", _onboarding())
    assert e.value.status_code == 409


@pytest.mark.asyncio
async def test_profilo_self_422_se_minorenne():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    svc.repo.get_by_keycloak_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as e:
        await svc.crea_profilo_self("kc", "a@b.it", _onboarding(cf="RSSMRA10A01H501A", nascita=date(2015, 1, 1)))
    # può fallire per CF o per minore età: entrambi 422
    assert e.value.status_code == 422


@pytest.mark.asyncio
async def test_profilo_self_422_cf_non_valido():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    svc.repo.get_by_keycloak_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as e:
        await svc.crea_profilo_self("kc", "a@b.it", _onboarding(cf="MRTMTT91D08F205A"))
    assert e.value.status_code == 422


@pytest.mark.asyncio
async def test_profilo_self_422_email_mancante():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    svc.repo.get_by_keycloak_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as e:
        await svc.crea_profilo_self("kc", None, _onboarding())
    assert e.value.status_code == 422


# ── avvia_tesseramento: blocca senza documento ────────────────────────────────

@pytest.mark.asyncio
async def test_tesseramento_409_senza_documento():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    svc._ha_documento = AsyncMock(return_value=False)
    socio = MagicMock(); socio.id = uuid4()
    with pytest.raises(HTTPException) as e:
        await svc.avvia_tesseramento(socio, "volley", is_minore=False)
    assert e.value.status_code == 409
    assert "documento" in e.value.detail.lower()


# ── minori (Fase 3) ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_minore_422_se_adulto():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    tutore = MagicMock(); tutore.id = uuid4()
    with pytest.raises(HTTPException) as e:
        await svc.crea_minore(tutore, _onboarding(cf="MRTMTT91D08F205J", nascita=date(1990, 1, 1)))
    assert e.value.status_code == 422


@pytest.mark.asyncio
async def test_minore_422_cf_non_valido():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    tutore = MagicMock(); tutore.id = uuid4()
    with pytest.raises(HTTPException) as e:
        await svc.crea_minore(tutore, _onboarding(cf="XXXYYY10A01H501A", nascita=date(2015, 1, 1)))
    assert e.value.status_code == 422


@pytest.mark.asyncio
async def test_tesseramento_minore_409_senza_tutela():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    svc._ha_documento = AsyncMock(side_effect=lambda socio_id, tipo: tipo == "identita")
    minore = MagicMock(); minore.id = uuid4()
    with pytest.raises(HTTPException) as e:
        await svc.avvia_tesseramento(minore, "volley", is_minore=True, pagante_socio_id=uuid4())
    assert e.value.status_code == 409
    assert "tutela" in e.value.detail.lower()


@pytest.mark.asyncio
async def test_tesseramento_minore_409_senza_doppio_consenso():
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    svc._ha_documento = AsyncMock(return_value=True)          # identità + tutela presenti
    svc._consensi_ok = AsyncMock(return_value=False)          # manca il doppio consenso
    minore = MagicMock(); minore.id = uuid4()
    with pytest.raises(HTTPException) as e:
        await svc.avvia_tesseramento(minore, "volley", is_minore=True, pagante_socio_id=uuid4())
    assert e.value.status_code == 409
    assert "consenso" in e.value.detail.lower()


# ── conferma_pagamento_tessera: attiva provvisoria ────────────────────────────

@pytest.mark.asyncio
async def test_conferma_pagamento_attiva_provvisoria():
    from modules.soci.tesseramento_service import TesseramentoService

    pagamento = MagicMock()
    pagamento.stato = "in_attesa_pagamento"
    pagamento.tessera_id = uuid4()

    tessera = MagicMock()
    tessera.id = pagamento.tessera_id

    paid = MagicMock(); paid.payment_status = "paid"; paid.payment_intent = "pi_x"

    db = _mock_db()
    r1 = MagicMock(); r1.scalar_one_or_none.return_value = pagamento
    r2 = MagicMock(); r2.scalar_one_or_none.return_value = tessera
    db.execute = AsyncMock(side_effect=[r1, r2])

    with patch("modules.soci.tesseramento_service.asyncio.to_thread",
               new_callable=AsyncMock, return_value=paid):
        await TesseramentoService(db).conferma_pagamento_tessera("cs_test")

    assert pagamento.stato == "pagato"
    assert tessera.stato == "attiva"
    assert tessera.verifica_stato == "in_verifica"
    assert tessera.verifica_scadenza is not None


# ── verifica staff (Fase 4) ───────────────────────────────────────────────────

def _res_one(obj):
    r = MagicMock(); r.scalar_one_or_none.return_value = obj; return r


def _res_first(obj):
    r = MagicMock(); r.scalars.return_value.first.return_value = obj; return r


@pytest.mark.asyncio
async def test_conferma_verifica():
    from modules.soci.tesseramento_service import TesseramentoService
    t = MagicMock(); t.verifica_stato = "in_verifica"
    db = _mock_db(); db.execute = AsyncMock(return_value=_res_one(t))
    verificatore = uuid4()
    await TesseramentoService(db).conferma_verifica(uuid4(), verificatore)
    assert t.verifica_stato == "confermata"
    assert t.verificata_da == verificatore
    assert t.verificata_at is not None


@pytest.mark.asyncio
async def test_conferma_verifica_409_se_non_in_verifica():
    from modules.soci.tesseramento_service import TesseramentoService
    t = MagicMock(); t.verifica_stato = "confermata"
    db = _mock_db(); db.execute = AsyncMock(return_value=_res_one(t))
    with pytest.raises(HTTPException) as e:
        await TesseramentoService(db).conferma_verifica(uuid4(), uuid4())
    assert e.value.status_code == 409


@pytest.mark.asyncio
async def test_rifiuta_verifica_erogazione_liberale():
    from modules.soci.tesseramento_service import TesseramentoService
    t = MagicMock(); t.verifica_stato = "in_verifica"
    pag = MagicMock(); pag.stato = "pagato"
    db = _mock_db()
    db.execute = AsyncMock(side_effect=[_res_one(t), _res_first(pag)])
    await TesseramentoService(db).rifiuta_verifica(uuid4(), uuid4())
    assert t.verifica_stato == "rifiutata"
    assert t.stato == "sospesa"
    assert pag.stato == "erogazione_liberale"


@pytest.mark.asyncio
async def test_auto_conferma_scadute():
    from modules.soci.tesseramento_service import TesseramentoService
    t1, t2 = MagicMock(), MagicMock()
    for t in (t1, t2):
        t.verifica_stato = "in_verifica"
    db = _mock_db()
    r = MagicMock(); r.scalars.return_value.all.return_value = [t1, t2]
    db.execute = AsyncMock(return_value=r)
    n = await TesseramentoService(db).auto_conferma_scadute()
    assert n == 2
    assert t1.verifica_stato == "confermata" and t2.verifica_stato == "confermata"
    assert t1.verificata_da is not t1  # verificata_da resta None (silenzio-assenso), non impostato a un socio
