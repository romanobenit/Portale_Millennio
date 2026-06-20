"""Unit tests per NFTService.avvia_acquisto e tasks.mint._segna_fallito."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from schemas.nft import AcquistoNFTRequest, OreSelezioneNFT


# ── factory helpers ───────────────────────────────────────────────────────────

def _tessera_result(tessera):
    """db.execute() il cui .scalars().first() restituisce tessera."""
    r = MagicMock()
    r.scalars.return_value.first.return_value = tessera
    return r


def _scalar_one_or_none_result(obj):
    """db.execute() il cui .scalar_one_or_none() restituisce obj."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _scalars_all_result(items):
    """db.execute() il cui .scalars().all() restituisce items."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    return r


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.commit = AsyncMock()
    return db


def _fake_tessera() -> MagicMock:
    t = MagicMock()
    t.numero_tessera = "VOL-2026-00001"
    return t


def _fake_wallet() -> MagicMock:
    w = MagicMock()
    w.wallet_address = "0xABCDEF1234"
    return w


def _fake_riepilogo(slot_id) -> MagicMock:
    r = MagicMock()
    r.costo_totale = 90.0
    r.selezione = [{"slot_id": str(slot_id)}]
    return r


def _fake_stripe_session() -> MagicMock:
    s = MagicMock()
    s.id = "cs_test_abc123"
    s.url = "https://checkout.stripe.com/pay/cs_test_abc123"
    return s


# ── test 1: avvia_acquisto happy path ────────────────────────────────────────

@pytest.mark.asyncio
async def test_avvia_acquisto_happy_path():
    """Socio con tessera attiva, ore libere → Stripe session creata correttamente."""
    from modules.nft.service import NFTService

    socio_id = uuid4()
    slot_id = uuid4()
    acquisto_id = uuid4()

    acquisto_mock = MagicMock()
    acquisto_mock.id = acquisto_id

    db = _mock_db()
    db.execute = AsyncMock(side_effect=[
        _tessera_result(_fake_tessera()),       # _verifica_tessera_attiva
        _scalar_one_or_none_result(_fake_wallet()),  # _get_o_crea_wallet (wallet esiste)
    ])

    data = AcquistoNFTRequest(
        selezione=[OreSelezioneNFT(slot_id=slot_id, ore=[8, 9])],
        acquisto_per_minore=False,
    )

    with patch("modules.nft.service.CalendarioService") as MockCal, \
         patch("modules.nft.service.AcquistoNFT", return_value=acquisto_mock), \
         patch("modules.nft.service.AcquistoNFTSlot", return_value=MagicMock()), \
         patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:

        MockCal.return_value.lock_selezione = AsyncMock(
            return_value=_fake_riepilogo(slot_id)
        )
        mock_thread.return_value = _fake_stripe_session()

        service = NFTService(db)
        result = await service.avvia_acquisto(socio_id, data)

    assert result.stripe_session_id == "cs_test_abc123"
    assert result.stripe_checkout_url == "https://checkout.stripe.com/pay/cs_test_abc123"
    assert result.importo_eur == 90.0
    assert result.slot_count == 1
    assert result.id == acquisto_id
    MockCal.return_value.lock_selezione.assert_awaited_once()


# ── test 2: avvia_acquisto senza tessera attiva → 403 ────────────────────────

@pytest.mark.asyncio
async def test_avvia_acquisto_senza_tessera_attiva():
    """Socio senza tessera attiva → HTTPException 403."""
    from modules.nft.service import NFTService

    socio_id = uuid4()
    slot_id = uuid4()

    db = _mock_db()
    db.execute = AsyncMock(return_value=_tessera_result(None))  # nessuna tessera

    data = AcquistoNFTRequest(
        selezione=[OreSelezioneNFT(slot_id=slot_id, ore=[8])],
    )

    with patch("modules.nft.service.CalendarioService"):
        service = NFTService(db)
        with pytest.raises(HTTPException) as exc_info:
            await service.avvia_acquisto(socio_id, data)

    assert exc_info.value.status_code == 403
    assert "tessera" in exc_info.value.detail.lower()


# ── test 3: avvia_acquisto per minore, richiedente non è tutore → 403 ─────────

@pytest.mark.asyncio
async def test_avvia_acquisto_minore_tutore_non_valido():
    """Acquisto per minore ma il richiedente non risulta tutore → HTTPException 403."""
    from modules.nft.service import NFTService

    socio_id = uuid4()
    minore_id = uuid4()
    slot_id = uuid4()

    db = _mock_db()
    db.execute = AsyncMock(side_effect=[
        _tessera_result(_fake_tessera()),       # _verifica_tessera_attiva
        _scalar_one_or_none_result(None),       # _verifica_tutore_minore → non trovato
    ])

    data = AcquistoNFTRequest(
        selezione=[OreSelezioneNFT(slot_id=slot_id, ore=[8])],
        acquisto_per_minore=True,
        minore_id=minore_id,
    )

    with patch("modules.nft.service.CalendarioService"):
        service = NFTService(db)
        with pytest.raises(HTTPException) as exc_info:
            await service.avvia_acquisto(socio_id, data)

    assert exc_info.value.status_code == 403
    assert "minore" in exc_info.value.detail.lower()


# ── test 4: avvia_acquisto ore già vendute → 409 ─────────────────────────────

@pytest.mark.asyncio
async def test_avvia_acquisto_ore_gia_vendute():
    """lock_selezione rifiuta ore già vendute: l'HTTPException 409 viene propagata."""
    from modules.nft.service import NFTService

    socio_id = uuid4()
    slot_id = uuid4()

    db = _mock_db()
    db.execute = AsyncMock(return_value=_tessera_result(_fake_tessera()))

    data = AcquistoNFTRequest(
        selezione=[OreSelezioneNFT(slot_id=slot_id, ore=[8])],
    )

    with patch("modules.nft.service.CalendarioService") as MockCal:
        MockCal.return_value.lock_selezione = AsyncMock(
            side_effect=HTTPException(status_code=409, detail="Ore non disponibili")
        )

        service = NFTService(db)
        with pytest.raises(HTTPException) as exc_info:
            await service.avvia_acquisto(socio_id, data)

    assert exc_info.value.status_code == 409


# ── helper: db.execute il cui .scalar_one() / .all() restituiscono valori ─────

def _scalar_one_result(obj):
    r = MagicMock()
    r.scalar_one.return_value = obj
    return r


def _all_tuples_result(tuples):
    """db.execute() il cui .all() restituisce una lista di tuple (es. JOIN)."""
    r = MagicMock()
    r.all.return_value = tuples
    return r


def _session_cm(db):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ── test 5: _segna_fallito rimborsa e rilascia le ore claimate ────────────────

@pytest.mark.asyncio
async def test_segna_fallito_rimborsa_e_rilascia():
    """
    Mint fallito definitivo → rimborso Stripe + ore claimate rimosse da ore_vendute
    + stato 'rimborsato'. (Regression: prima non rimborsava — soldi presi senza NFT.)
    """
    from tasks.mint import _segna_fallito

    acquisto_id = uuid4()

    acquisto_mock = MagicMock()
    acquisto_mock.stato = "pagato"
    acquisto_mock.stripe_payment_id = "pi_test"

    link_mock = MagicMock()
    link_mock.ore_acquistate = [8]

    slot_mock = MagicMock()
    slot_mock.ore_vendute = [8]          # ora claimata alla conferma
    slot_mock.ore_in_lock = []
    slot_mock.ora_inizio = MagicMock(hour=8)
    slot_mock.ore_totali = 5

    db = _mock_db()
    db.execute = AsyncMock(side_effect=[
        _scalar_one_or_none_result(acquisto_mock),   # AcquistoNFT lookup
        _all_tuples_result([(link_mock, slot_mock)]),  # JOIN link+slot FOR UPDATE
    ])

    with patch("tasks.mint.AsyncSessionLocal", return_value=_session_cm(db)), \
         patch("tasks.mint.asyncio.to_thread", new_callable=AsyncMock) as mock_refund:
        await _segna_fallito(acquisto_id)

    mock_refund.assert_awaited_once()          # stripe.Refund.create invocato
    assert acquisto_mock.stato == "rimborsato"
    assert slot_mock.ore_vendute == []         # ora rilasciata
    assert slot_mock.nft_token_id is None
    assert slot_mock.stato == "libero"
    db.commit.assert_awaited_once()


# ── test 6 (#1): _run_mint salta il mint se token_id già presente (checkpoint) ─

@pytest.mark.asyncio
async def test_run_mint_idempotente_salta_se_gia_mintato():
    """Se token_id è già persistito (checkpoint), il retry NON ri-minta on-chain."""
    from tasks.mint import _run_mint

    acquisto_id = uuid4()
    slot_id = uuid4()

    acquisto_mock = MagicMock()
    acquisto_mock.stato = "pagato"
    acquisto_mock.token_id = 555            # già mintato in un tentativo precedente
    acquisto_mock.importo_eur = 100

    link_mock = MagicMock()
    link_mock.slot_calendario_id = slot_id
    link_mock.ore_acquistate = [8]

    from datetime import date
    slot_mock = MagicMock()
    slot_mock.id = slot_id
    slot_mock.data = date(2027, 1, 4)
    slot_mock.fascia = "mattina"

    db = _mock_db()
    db.execute = AsyncMock(side_effect=[
        _scalar_one_result(acquisto_mock),          # AcquistoNFT
        _scalars_all_result([link_mock]),           # links
        _scalars_all_result([slot_mock]),           # slots
        _tessera_result(_fake_tessera()),           # tessera
        _scalar_one_result(_fake_wallet()),         # wallet
    ])

    with patch("tasks.mint.AsyncSessionLocal", return_value=_session_cm(db)), \
         patch("tasks.mint.genera_ical_content", return_value="ICAL"), \
         patch("tasks.mint.calcola_sha256", return_value="hash"), \
         patch("tasks.mint.costruisci_metadati_nft", return_value={}), \
         patch("tasks.mint.upload_json_to_ipfs", new_callable=AsyncMock, return_value="ipfs://x"), \
         patch("modules.nft.blockchain.mint_nft", new_callable=AsyncMock) as m_mint, \
         patch("modules.nft.blockchain.update_token_uri", new_callable=AsyncMock) as m_upd:
        await _run_mint(acquisto_id)

    m_mint.assert_not_awaited()                 # NESSUN nuovo mint on-chain
    m_upd.assert_awaited_once()                 # ripreso dal checkpoint
    assert acquisto_mock.token_id == 555
    assert acquisto_mock.stato == "mintato"


# ── test 7 (#4): conferma_pagamento blocca la doppia vendita e rimborsa ───────

@pytest.mark.asyncio
async def test_conferma_pagamento_double_sell_rimborso():
    """Ora già venduta da altri (lock scaduto) → rimborso, niente mint, ritorna None."""
    from modules.nft.service import NFTService

    acquisto_mock = MagicMock()
    acquisto_mock.id = uuid4()
    acquisto_mock.stato = "in_attesa_pagamento"

    link_mock = MagicMock()
    link_mock.slot_calendario_id = uuid4()
    link_mock.ore_acquistate = [8]

    slot_mock = MagicMock()
    slot_mock.ore_vendute = [8]              # GIÀ venduta da un altro acquisto → conflitto
    slot_mock.ore_in_lock = [8]
    slot_mock.ora_inizio = MagicMock(hour=8)
    slot_mock.ore_totali = 5

    paid_session = MagicMock()
    paid_session.payment_status = "paid"
    paid_session.payment_intent = "pi_x"

    db = _mock_db()
    db.execute = AsyncMock(side_effect=[
        _scalar_one_or_none_result(acquisto_mock),   # acquisto by session
        _scalars_all_result([link_mock]),            # links
        _scalar_one_or_none_result(slot_mock),       # slot FOR UPDATE (conflitto)
        _scalar_one_or_none_result(slot_mock),       # slot FOR UPDATE (rilascio)
    ])

    with patch("modules.nft.service.CalendarioService"), \
         patch("modules.nft.service.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        # 1ª chiamata: Session.retrieve (paid) | 2ª chiamata: Refund.create
        mock_thread.side_effect = [paid_session, {"id": "re_x"}]
        result = await NFTService(db).conferma_pagamento("cs_test")

    assert result is None                         # niente mint
    assert acquisto_mock.stato == "rimborsato"
    assert mock_thread.await_count == 2           # retrieve + refund


# ── test 8 (#6): conferma_pagamento ritorna l'id e NON accoda il task ─────────

@pytest.mark.asyncio
async def test_conferma_pagamento_ritorna_id_senza_dispatch():
    """conferma_pagamento ritorna l'id da mintare; il dispatch avviene dopo il commit."""
    from modules.nft.service import NFTService

    acq_id = uuid4()
    acquisto_mock = MagicMock()
    acquisto_mock.id = acq_id
    acquisto_mock.stato = "in_attesa_pagamento"

    link_mock = MagicMock()
    link_mock.slot_calendario_id = uuid4()
    link_mock.ore_acquistate = [8]

    slot_mock = MagicMock()
    slot_mock.ore_vendute = []               # libera → nessun conflitto
    slot_mock.ore_in_lock = [8]
    slot_mock.ora_inizio = MagicMock(hour=8)
    slot_mock.ore_totali = 5

    paid_session = MagicMock()
    paid_session.payment_status = "paid"
    paid_session.payment_intent = "pi_y"

    db = _mock_db()
    db.execute = AsyncMock(side_effect=[
        _scalar_one_or_none_result(acquisto_mock),   # acquisto by session
        _scalars_all_result([link_mock]),            # links
        _scalar_one_or_none_result(slot_mock),       # slot FOR UPDATE (claim)
    ])

    with patch("modules.nft.service.CalendarioService"), \
         patch("modules.nft.service.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = paid_session
        result = await NFTService(db).conferma_pagamento("cs_test")

    assert result == acq_id                       # id da accodare DOPO il commit
    assert acquisto_mock.stato == "pagato"
