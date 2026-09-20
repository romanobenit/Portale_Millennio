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
    db.delete = AsyncMock()
    db.rollback = AsyncMock()
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


# ── crea_profilo_self: collegamento a profilo esistente per email ─────────────

@pytest.mark.asyncio
async def test_profilo_self_409_se_esistente_non_verificato():
    """
    Un profilo pre-creato dallo staff (es. import CSV) non va MAI collegato/
    sovrascritto da un login con email non verificata: altrimenti chiunque
    conosca l'email di un socio potrebbe registrarsi e impossessarsene.
    """
    from modules.soci.tesseramento_service import TesseramentoService
    svc = TesseramentoService(_mock_db())
    svc.repo.get_by_keycloak_id = AsyncMock(return_value=None)
    esistente = MagicMock()
    esistente.keycloak_user_id = None
    svc.repo.get_by_email = AsyncMock(return_value=esistente)
    with pytest.raises(HTTPException) as e:
        await svc.crea_profilo_self("kc", "a@b.it", _onboarding(), email_verified=False)
    assert e.value.status_code == 409
    assert esistente.keycloak_user_id is None  # non collegato


@pytest.mark.asyncio
async def test_profilo_self_collega_se_email_verificata():
    from datetime import datetime
    from modules.soci.tesseramento_service import TesseramentoService

    class _SocioEsistente:
        pass

    esistente = _SocioEsistente()
    esistente.id = uuid4()
    esistente.keycloak_user_id = None
    esistente.nome = "Vecchio"
    esistente.cognome = "Nome"
    esistente.data_nascita = date(1990, 1, 1)
    esistente.codice_fiscale = "MRTMTT91D08F205J"
    esistente.indirizzo = None
    esistente.email = "a@b.it"
    esistente.telefono = None
    esistente.foto_url = None
    esistente.is_minor = False
    esistente.tutore_id = None
    esistente.sport = []
    esistente.created_at = datetime(2026, 1, 1)
    esistente.updated_at = datetime(2026, 1, 1)

    svc = TesseramentoService(_mock_db())
    svc.repo.get_by_keycloak_id = AsyncMock(return_value=None)
    svc.repo.get_by_email = AsyncMock(return_value=esistente)
    dati = _onboarding()
    risultato = await svc.crea_profilo_self("kc-sub", "a@b.it", dati, email_verified=True)
    assert esistente.keycloak_user_id == "kc-sub"
    assert esistente.nome == dati.nome
    assert risultato.nome == dati.nome


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


# ── avvia_tesseramento: race concorrente (indice unico parziale) ──────────────

@pytest.mark.asyncio
async def test_avvia_tesseramento_409_su_race_concorrente():
    """
    Due richieste concorrenti (doppio click, due tab) superano entrambe il
    controllo applicativo "esistente" (un SELECT senza lock, nessuna riga da
    bloccare). L'IntegrityError dell'indice unico parziale a livello DB
    (migration 20260919_120000) deve tradursi in un 409 pulito, non in un 500.
    """
    from sqlalchemy.exc import IntegrityError

    from modules.soci.tesseramento_service import TesseramentoService

    db = _mock_db()
    svc = TesseramentoService(db)
    svc._ha_documento = AsyncMock(return_value=True)
    svc._consensi_ok = AsyncMock(return_value=True)
    svc._quota = AsyncMock(return_value=MagicMock(importo_eur=50))

    nessuna_tessera = MagicMock()
    nessuna_tessera.scalars.return_value.first.return_value = None
    db.execute = AsyncMock(return_value=nessuna_tessera)
    db.flush = AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate key")))

    socio = MagicMock(); socio.id = uuid4()
    with patch(
        "modules.soci.tesseramento_service._genera_numero_tessera",
        new=AsyncMock(return_value="VOL-2026-00001"),
    ):
        with pytest.raises(HTTPException) as e:
            await svc.avvia_tesseramento(socio, "volley", is_minore=False)
    assert e.value.status_code == 409
    db.rollback.assert_awaited()


# ── gestisci_pagamento_fallito: sessione scaduta / pagamento fallito ──────────

@pytest.mark.asyncio
async def test_gestisci_pagamento_fallito_rimuove_placeholder():
    """
    Un checkout abbandonato/fallito deve rimuovere la tessera+pagamento
    placeholder creati da avvia_tesseramento, altrimenti il controllo
    anti-doppione blocca per sempre un nuovo tentativo.
    """
    from modules.soci.tesseramento_service import TesseramentoService

    pagamento = MagicMock()
    pagamento.id = uuid4()
    pagamento.stato = "in_attesa_pagamento"
    pagamento.tessera_id = uuid4()

    tessera = MagicMock()
    tessera.id = pagamento.tessera_id
    tessera.stato = "in_attesa_pagamento"

    db = _mock_db()
    r1 = MagicMock(); r1.scalar_one_or_none.return_value = pagamento
    r2 = MagicMock(); r2.scalar_one_or_none.return_value = tessera
    db.execute = AsyncMock(side_effect=[r1, r2])

    await TesseramentoService(db).gestisci_pagamento_fallito(stripe_session_id="cs_test")

    db.delete.assert_any_call(pagamento)
    db.delete.assert_any_call(tessera)


@pytest.mark.asyncio
async def test_gestisci_pagamento_fallito_idempotente_se_gia_pagato():
    """Il webhook di scadenza può arrivare in ritardo, dopo che il pagamento è già confermato: no-op."""
    from modules.soci.tesseramento_service import TesseramentoService

    pagamento = MagicMock()
    pagamento.stato = "pagato"

    db = _mock_db()
    r1 = MagicMock(); r1.scalar_one_or_none.return_value = pagamento
    db.execute = AsyncMock(return_value=r1)

    await TesseramentoService(db).gestisci_pagamento_fallito(pagamento_tessera_id=uuid4())

    db.delete.assert_not_called()


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


# ── riprendi_pagamento: completare un tesseramento avviato in precedenza ──────

@pytest.mark.asyncio
async def test_riprendi_pagamento_404_se_non_in_attesa():
    from modules.soci.tesseramento_service import TesseramentoService
    tessera = MagicMock(); tessera.stato = "attiva"
    db = _mock_db()
    r = MagicMock(); r.scalar_one_or_none.return_value = tessera
    db.execute = AsyncMock(return_value=r)
    with pytest.raises(HTTPException) as e:
        await TesseramentoService(db).riprendi_pagamento(uuid4(), uuid4())
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_riprendi_pagamento_riusa_sessione_aperta():
    """Se la sessione Stripe esistente è ancora 'open', va riusata senza crearne una nuova."""
    from modules.soci.tesseramento_service import TesseramentoService

    tessera = MagicMock(); tessera.id = uuid4(); tessera.stato = "in_attesa_pagamento"; tessera.sport = "volley"
    pagamento = MagicMock()
    pagamento.id = uuid4()
    pagamento.stripe_session_id = "cs_test_esistente"
    pagamento.importo_eur = 50
    pagamento.stato = "in_attesa_pagamento"

    db = _mock_db()
    r1 = MagicMock(); r1.scalar_one_or_none.return_value = tessera
    r2 = MagicMock(); r2.scalars.return_value.first.return_value = pagamento
    db.execute = AsyncMock(side_effect=[r1, r2])

    sessione_aperta = MagicMock(); sessione_aperta.status = "open"; sessione_aperta.url = "https://checkout.stripe.com/vecchia"

    with patch("modules.soci.tesseramento_service.asyncio.to_thread",
               new_callable=AsyncMock, return_value=sessione_aperta):
        res = await TesseramentoService(db).riprendi_pagamento(tessera.id, uuid4())

    assert res.stripe_checkout_url == "https://checkout.stripe.com/vecchia"
    assert pagamento.stripe_session_id == "cs_test_esistente"  # non sovrascritta: sessione riusata


@pytest.mark.asyncio
async def test_riprendi_pagamento_ricrea_sessione_scaduta():
    """Se la sessione Stripe esistente è scaduta, ne va creata una nuova per lo stesso pagamento."""
    from modules.soci.tesseramento_service import TesseramentoService

    tessera = MagicMock(); tessera.id = uuid4(); tessera.stato = "in_attesa_pagamento"; tessera.sport = "volley"
    pagamento = MagicMock()
    pagamento.id = uuid4()
    pagamento.stripe_session_id = "cs_test_scaduta"
    pagamento.importo_eur = 50
    pagamento.stato = "in_attesa_pagamento"

    db = _mock_db()
    r1 = MagicMock(); r1.scalar_one_or_none.return_value = tessera
    r2 = MagicMock(); r2.scalars.return_value.first.return_value = pagamento
    db.execute = AsyncMock(side_effect=[r1, r2])

    sessione_scaduta = MagicMock(); sessione_scaduta.status = "expired"
    sessione_nuova = MagicMock(); sessione_nuova.id = "cs_test_nuova"; sessione_nuova.url = "https://checkout.stripe.com/nuova"

    with patch("modules.soci.tesseramento_service.asyncio.to_thread",
               new_callable=AsyncMock, side_effect=[sessione_scaduta, sessione_nuova]):
        res = await TesseramentoService(db).riprendi_pagamento(tessera.id, uuid4())

    assert res.stripe_checkout_url == "https://checkout.stripe.com/nuova"
    assert pagamento.stripe_session_id == "cs_test_nuova"


@pytest.mark.asyncio
async def test_riprendi_pagamento_409_se_gia_completato():
    """Se la sessione risulta 'complete' (webhook in ritardo), non va creata una seconda sessione."""
    from modules.soci.tesseramento_service import TesseramentoService

    tessera = MagicMock(); tessera.id = uuid4(); tessera.stato = "in_attesa_pagamento"; tessera.sport = "volley"
    pagamento = MagicMock()
    pagamento.stripe_session_id = "cs_test_completata"
    pagamento.importo_eur = 50
    pagamento.stato = "in_attesa_pagamento"

    db = _mock_db()
    r1 = MagicMock(); r1.scalar_one_or_none.return_value = tessera
    r2 = MagicMock(); r2.scalars.return_value.first.return_value = pagamento
    db.execute = AsyncMock(side_effect=[r1, r2])

    sessione_completata = MagicMock(); sessione_completata.status = "complete"

    with patch("modules.soci.tesseramento_service.asyncio.to_thread",
               new_callable=AsyncMock, return_value=sessione_completata):
        with pytest.raises(HTTPException) as e:
            await TesseramentoService(db).riprendi_pagamento(tessera.id, uuid4())
    assert e.value.status_code == 409


# ── lista_tesserati: elenco completo per la dirigenza ──────────────────────────

@pytest.mark.asyncio
async def test_lista_tesserati_mappa_righe_con_tutore():
    from modules.soci.tesseramento_service import TesseramentoService

    tessera = MagicMock()
    tessera.id = uuid4()
    tessera.numero_tessera = "SOS-2026-00003"
    tessera.sport = "sostenitore"
    tessera.stato = "attiva"
    tessera.anno_sportivo = "2026-2027"
    tessera.data_scadenza = date(2027, 6, 30)
    tessera.verifica_stato = "confermata"

    minore = MagicMock()
    minore.id = uuid4()
    minore.nome = "Luca"
    minore.cognome = "Bianchi"
    minore.codice_fiscale = "BNCLCU15A01H501U"
    minore.is_minor = True

    tutore = MagicMock()
    tutore.id = uuid4()
    tutore.nome = "Anna"
    tutore.cognome = "Bianchi"
    tutore.codice_fiscale = "BNCNNA80A41H501U"
    tutore.is_minor = False

    db = _mock_db()
    result = MagicMock()
    result.all.return_value = [(tessera, minore, tutore)]
    db.execute = AsyncMock(return_value=result)

    out = await TesseramentoService(db).lista_tesserati()

    assert len(out) == 1
    assert out[0].numero_tessera == "SOS-2026-00003"
    assert out[0].socio.cognome == "Bianchi"
    assert out[0].socio.is_minor is True
    assert out[0].tutore is not None
    assert out[0].tutore.nome == "Anna"


@pytest.mark.asyncio
async def test_lista_tesserati_senza_tutore():
    from modules.soci.tesseramento_service import TesseramentoService

    tessera = MagicMock()
    tessera.id = uuid4()
    tessera.numero_tessera = "VOL-2026-00001"
    tessera.sport = "volley"
    tessera.stato = "scaduta"
    tessera.anno_sportivo = "2025-2026"
    tessera.data_scadenza = date(2026, 6, 30)
    tessera.verifica_stato = "confermata"

    socio = MagicMock()
    socio.id = uuid4()
    socio.nome = "Mario"
    socio.cognome = "Rossi"
    socio.codice_fiscale = "RSSMRA80A01H501U"
    socio.is_minor = False

    db = _mock_db()
    result = MagicMock()
    result.all.return_value = [(tessera, socio, None)]
    db.execute = AsyncMock(return_value=result)

    out = await TesseramentoService(db).lista_tesserati(stato="scaduta")

    assert len(out) == 1
    assert out[0].stato == "scaduta"
    assert out[0].tutore is None


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
