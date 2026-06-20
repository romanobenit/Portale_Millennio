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


# ── test 5: _segna_fallito rilascia slot bloccato → stato "libero" ────────────

@pytest.mark.asyncio
async def test_segna_fallito_rilascia_slot_bloccato():
    """_segna_fallito marca l'acquisto come 'fallito' e riporta lo slot a 'libero'."""
    from tasks.mint import _segna_fallito

    acquisto_id = uuid4()
    slot_id = uuid4()

    acquisto_mock = MagicMock()
    acquisto_mock.stato = "in_attesa_pagamento"

    link_mock = MagicMock()
    link_mock.slot_calendario_id = slot_id

    slot_mock = MagicMock()
    slot_mock.stato = "bloccato"
    slot_mock.ore_vendute = []  # nessuna ora venduta → dopo cleanup: "libero"

    db = _mock_db()
    db.execute = AsyncMock(side_effect=[
        _scalar_one_or_none_result(acquisto_mock),  # AcquistoNFT lookup
        _scalars_all_result([link_mock]),            # AcquistoNFTSlot links
        _scalars_all_result([slot_mock]),            # SlotCalendario
    ])

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("tasks.mint.AsyncSessionLocal", return_value=mock_session_cm):
        await _segna_fallito(acquisto_id)

    assert acquisto_mock.stato == "fallito"
    assert slot_mock.stato == "libero"
    assert slot_mock.ore_in_lock == []
    assert slot_mock.bloccato_fino_a is None
    assert slot_mock.nft_token_id is None
    db.commit.assert_awaited_once()
