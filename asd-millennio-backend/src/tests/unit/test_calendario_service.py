from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from modules.nft.ical import calcola_sha256, genera_ical_content


def make_slot(data: date, fascia: str, ora_inizio: time, ore_totali: int):
    slot = MagicMock()
    slot.data = data
    slot.fascia = fascia
    slot.ora_inizio = ora_inizio
    slot.ore_totali = ore_totali
    return slot


# ── iCal: un VEVENT per ogni ora ────────────────────────────────────────────

def test_genera_ical_header():
    slots = [make_slot(date(2027, 3, 3), "mattina", time(8, 0), 5)]
    content = genera_ical_content(slots, 42, "VOL-2026-00001", "0xContractAddress")

    assert content.startswith("BEGIN:VCALENDAR")
    assert "END:VCALENDAR" in content
    assert "Token ID: 42" in content
    assert "VOL-2026-00001" in content
    assert "Palasirio" in content


def test_genera_ical_un_vevent_per_ora_mattina():
    """Fascia mattina (5 ore: 8-12) → 5 VEVENTs."""
    slots = [make_slot(date(2027, 3, 3), "mattina", time(8, 0), 5)]
    content = genera_ical_content(slots, 1, "VOL-2026-00001", "0xABC")
    assert content.count("BEGIN:VEVENT") == 5
    assert content.count("END:VEVENT") == 5


def test_genera_ical_un_vevent_per_ora_notte():
    """Fascia notte (8 ore: 0-7) → 8 VEVENTs."""
    slots = [make_slot(date(2027, 3, 3), "notte", time(0, 0), 8)]
    content = genera_ical_content(slots, 7, "BDM-2026-00002", "0xABC")
    assert content.count("BEGIN:VEVENT") == 8


def test_genera_ical_un_vevent_per_ora_pomeriggio():
    """Fascia pomeriggio (2 ore: 13-14) → 2 VEVENTs."""
    slots = [make_slot(date(2027, 3, 3), "pomeriggio", time(13, 0), 2)]
    content = genera_ical_content(slots, 99, "PCK-2026-00010", "0xABC")
    assert content.count("BEGIN:VEVENT") == 2


def test_genera_ical_ore_per_slot_parziali():
    """Con ore_per_slot esplicite, genera solo le ore richieste."""
    slot = make_slot(date(2027, 3, 3), "mattina", time(8, 0), 5)
    slot.id = "test-uuid"
    content = genera_ical_content(
        [slot], 5, "VOL-2026-00003", "0xABC",
        ore_per_slot={"test-uuid": [8, 9]}
    )
    assert content.count("BEGIN:VEVENT") == 2
    assert "DTSTART:20270303T080000" in content
    assert "DTSTART:20270303T090000" in content


def test_genera_ical_slot_multipli():
    """Due slot (mattina + pomeriggio) → 5+2 = 7 VEVENTs totali."""
    slots = [
        make_slot(date(2027, 3, 3), "mattina", time(8, 0), 5),
        make_slot(date(2027, 3, 3), "pomeriggio", time(13, 0), 2),
    ]
    content = genera_ical_content(slots, 10, "VOL-2026-00004", "0xABC")
    assert content.count("BEGIN:VEVENT") == 7


# ── SHA-256 ──────────────────────────────────────────────────────────────────

def test_calcola_sha256_determinismo():
    content = "test content ASD Millennio"
    sha = calcola_sha256(content)
    assert len(sha) == 64
    assert calcola_sha256(content) == sha


def test_calcola_sha256_diverso_per_contenuti_diversi():
    assert calcola_sha256("a") != calcola_sha256("b")


# ── PricingEngine (unit) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pricing_tariffa_base_fallback():
    """Senza regole nel DB, usa tariffe di default: notte=15, mattina=20, pomeriggio=25."""
    from decimal import Decimal
    from modules.calendario.pricing import _CachedRules, _TARIFFE_FALLBACK

    rules = _CachedRules([])
    assert rules.get_tariffa("notte") == Decimal("15.00")
    assert rules.get_tariffa("mattina") == Decimal("20.00")
    assert rules.get_tariffa("pomeriggio") == Decimal("25.00")


@pytest.mark.asyncio
async def test_pricing_mol_data_fallback_neutro():
    """Senza regole leva_data, moltiplicatore = 1.00."""
    from decimal import Decimal
    from modules.calendario.pricing import _CachedRules

    rules = _CachedRules([])
    assert rules.get_mol_data(100) == Decimal("1.00")
    assert rules.get_mol_data(3) == Decimal("1.00")


@pytest.mark.asyncio
async def test_pricing_sconto_promo_assente():
    """Senza sconti attivi, sconto = 0."""
    from decimal import Decimal
    from modules.calendario.pricing import _CachedRules

    rules = _CachedRules([])
    assert rules.get_sconto("mattina", date(2027, 3, 3)) == Decimal("0")


@pytest.mark.asyncio
async def test_pricing_prezzo_calcola_corretto():
    """Con tariffe di default (nessuna leva), 3 ore mattina = 3 × €20 = €60."""
    from decimal import Decimal
    from unittest.mock import AsyncMock, patch
    from modules.calendario.pricing import PricingEngine

    db = AsyncMock()

    # Mock _load_rules: restituisce regole vuote (usa fallback)
    # Mock _get_pct_libere_per_periodo: 100% libere → moltiplicatore scarsità 1.0.
    # Chiave per-mese: (fascia, anno, mese) dello slot.
    with patch.object(PricingEngine, "_load_rules") as mock_load, \
         patch.object(PricingEngine, "_get_pct_libere_per_periodo") as mock_pct:
        from modules.calendario.pricing import _CachedRules
        mock_load.return_value = _CachedRules([])
        mock_pct.return_value = {("mattina", 2027, 6): 100.0}

        engine = PricingEngine(db)
        slot = make_slot(date(2027, 6, 2), "mattina", time(8, 0), 5)
        slot.id = "slot-1"

        result = await engine.calcola_prezzo_selezione([
            {"slot": slot, "ore": [8, 9, 10]}
        ])

    assert result["costo_totale"] == 60.0
    assert result["ore_mattina"] == 3
    assert result["ore_notte"] == 0
    assert result["ore_pomeriggio"] == 0


# ── lock_selezione: doppio lock nello stesso flusso di acquisto ─────────────
# Bug reale riscontrato in produzione: il selettore calendario blocca le ore
# via POST /calendario/lock, poi avvia_acquisto richiama lock_selezione sulle
# STESSE ore → senza consenti_gia_bloccato, il secondo lock si autoconflitta
# credendo che l'ora sia "in lock da altro acquirente".

def _slot_bloccabile(ore_vendute=None, ore_in_lock=None) -> MagicMock:
    slot = MagicMock()
    slot.id = uuid4()
    slot.data = date(2027, 4, 1)
    slot.fascia = "mattina"
    slot.ora_inizio = time(8, 0)
    slot.ore_totali = 5
    slot.ore_vendute = ore_vendute or []
    slot.ore_in_lock = ore_in_lock or []
    slot.stato = "bloccato" if (ore_in_lock or ore_vendute) else "libero"
    slot.bloccato_fino_a = datetime.now(timezone.utc) + timedelta(minutes=20)
    return slot


def _db_con_slot(slot) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = slot
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    return db


from schemas.calendario import LockRequest, OreSelezione  # noqa: E402


@pytest.mark.asyncio
async def test_lock_selezione_ora_gia_in_lock_blocca_altro_acquirente():
    """Comportamento di default (default False): un'ora già in lock da altri → 409."""
    from modules.calendario.service import CalendarioService

    slot = _slot_bloccabile(ore_in_lock=[10])
    db = _db_con_slot(slot)
    req = LockRequest(selezione=[OreSelezione(slot_id=slot.id, ore=[10])])

    with pytest.raises(HTTPException) as exc_info:
        await CalendarioService(db).lock_selezione(req)

    assert exc_info.value.status_code == 409
    assert "altro acquirente" in exc_info.value.detail


@pytest.mark.asyncio
async def test_lock_selezione_consenti_gia_bloccato_estende_senza_conflitto():
    """Con consenti_gia_bloccato=True (avvia_acquisto), la stessa ora già in lock
    NON solleva più 409 — il lock viene semplicemente esteso."""
    from modules.calendario.service import CalendarioService

    slot = _slot_bloccabile(ore_in_lock=[10])
    db = _db_con_slot(slot)
    req = LockRequest(selezione=[OreSelezione(slot_id=slot.id, ore=[10])])

    with patch("modules.calendario.service.PricingEngine") as MockEngine:
        MockEngine.return_value.calcola_prezzo_selezione = AsyncMock(return_value={
            "ore_notte": 0, "ore_mattina": 1, "ore_pomeriggio": 0,
            "costo_totale": 20.0, "dettaglio": [],
        })
        riepilogo = await CalendarioService(db).lock_selezione(req, consenti_gia_bloccato=True)

    assert riepilogo.costo_totale == 20.0
    assert slot.ore_in_lock == [10]


@pytest.mark.asyncio
async def test_lock_selezione_ora_gia_venduta_blocca_sempre():
    """Anti double-sell reale: un'ora già in ore_vendute → 409 anche con
    consenti_gia_bloccato=True (protegge sempre contro le vendite reali)."""
    from modules.calendario.service import CalendarioService

    slot = _slot_bloccabile(ore_vendute=[10])
    db = _db_con_slot(slot)
    req = LockRequest(selezione=[OreSelezione(slot_id=slot.id, ore=[10])])

    with pytest.raises(HTTPException) as exc_info:
        await CalendarioService(db).lock_selezione(req, consenti_gia_bloccato=True)

    assert exc_info.value.status_code == 409
    assert "già venduta" in exc_info.value.detail
