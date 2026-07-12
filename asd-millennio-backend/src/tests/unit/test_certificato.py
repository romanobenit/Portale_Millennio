"""Test del certificato PDF, dell'email Resend (no-op) e dell'autorizzazione download."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


def _ore():
    return [
        {"data": date(2027, 1, 4), "fascia": "notte", "ora": 2},
        {"data": date(2027, 1, 4), "fascia": "mattina", "ora": 10},
        {"data": date(2027, 1, 5), "fascia": "pomeriggio", "ora": 13},
    ]


# ── generazione PDF ───────────────────────────────────────────────────────────

def test_certificato_produce_pdf_valido():
    from modules.nft.certificato import genera_certificato_pdf

    pdf = genera_certificato_pdf(
        nome="Benito", cognome="Romano", tessera_sostenitore="SOS-2026-00001",
        token_id=4, contract_address="0x3F1f4d0Abf6892AE7EE6BdceC65e857E3f10c6aE",
        wallet_address="0x0b1374F8519a4Aa837B5100cF8cB520656b087a4",
        mint_tx_hash="0x8656db73c4e1a09f7b2d5e46a1c8f30b9d2e5a71c0b4f8e6a2d9c1b7e2b8d6a0",
        ipfs_uri="ipfs://QmYy2bBht74eAF3tjfSUa2a78MCHrz4B5cFgw13QViDDZB",
        ore=_ore(), importo_eur=81.0, data_emissione=date(2026, 7, 11),
        polygonscan_base="https://amoy.polygonscan.com",
    )
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 2000


def test_certificato_gestisce_tx_mancante():
    """Token storico senza mint_tx_hash: il PDF si genera comunque (mostra '—')."""
    from modules.nft.certificato import genera_certificato_pdf

    pdf = genera_certificato_pdf(
        nome="Mario", cognome="Rossi", tessera_sostenitore=None,
        token_id=1, contract_address="0xabc", wallet_address="0xdef",
        mint_tx_hash=None, ipfs_uri="ipfs://Qm", ore=_ore(),
        importo_eur=40.0, data_emissione=date(2026, 7, 11),
        polygonscan_base="https://amoy.polygonscan.com",
    )
    assert pdf[:5] == b"%PDF-"


# ── email Resend ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_email_noop_senza_api_key():
    """Senza RESEND_API_KEY l'invio è un no-op che ritorna False, non solleva."""
    from modules.nft import email as email_mod

    with patch.object(email_mod.settings, "resend_api_key", ""):
        ok = await email_mod.invia_certificato_email(
            to="a@b.it", nome="Benito", token_id=4, ore_totali=5,
            importo="€ 81,00", polygonscan_url="https://x", pdf_bytes=b"%PDF-1",
        )
    assert ok is False


@pytest.mark.asyncio
async def test_email_invia_con_allegati():
    """Con API key configurata, POSTa a Resend con PDF e iCal in allegato."""
    from modules.nft import email as email_mod

    fake_resp = MagicMock(status_code=200, text="{}")
    client = MagicMock()
    client.post = AsyncMock(return_value=fake_resp)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch.object(email_mod.settings, "resend_api_key", "re_test"), \
         patch.object(email_mod.httpx, "AsyncClient", return_value=cm):
        ok = await email_mod.invia_certificato_email(
            to="socio@millennioasd.com", nome="Benito", token_id=4, ore_totali=5,
            importo="€ 81,00", polygonscan_url="https://amoy.polygonscan.com/token/x?a=4",
            pdf_bytes=b"%PDF-1", ical_content="BEGIN:VCALENDAR",
        )

    assert ok is True
    payload = client.post.call_args.kwargs["json"]
    assert len(payload["attachments"]) == 2
    assert payload["attachments"][0]["filename"].endswith(".pdf")
    assert payload["attachments"][1]["filename"].endswith(".ics")


# ── autorizzazione download certificato ───────────────────────────────────────

def _acquisto(stato="mintato", token_id=4, socio_id=None):
    a = MagicMock()
    a.stato = stato
    a.token_id = token_id
    a.socio_id = socio_id or uuid4()
    return a


def _db_returning(obj):
    db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = obj
    db.execute = AsyncMock(return_value=res)
    return db


@pytest.mark.asyncio
async def test_certificato_pdf_403_se_non_proprietario():
    from modules.nft.service import NFTService

    acq = _acquisto()
    db = _db_returning(acq)
    with pytest.raises(HTTPException) as exc:
        await NFTService(db).certificato_pdf(uuid4(), uuid4(), is_staff=False)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_certificato_pdf_409_se_non_mintato():
    from modules.nft.service import NFTService

    socio_id = uuid4()
    acq = _acquisto(stato="pagato", token_id=None, socio_id=socio_id)
    db = _db_returning(acq)
    with pytest.raises(HTTPException) as exc:
        await NFTService(db).certificato_pdf(uuid4(), socio_id, is_staff=False)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_certificato_pdf_staff_bypassa_proprieta():
    from modules.nft.service import NFTService

    acq = _acquisto()
    db = _db_returning(acq)
    with patch("modules.nft.certificato_builder.genera_pdf_certificato",
               new_callable=AsyncMock, return_value=b"%PDF-1") as gen:
        pdf = await NFTService(db).certificato_pdf(uuid4(), uuid4(), is_staff=True)
    assert pdf == b"%PDF-1"
    gen.assert_awaited_once()
