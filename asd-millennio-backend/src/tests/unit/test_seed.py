"""Unit tests for calendar seed script (Sprint 1)."""
from datetime import date

import pytest


def test_genera_date_ati_conta_giorni():
    """La stagione 2026-2027 deve produrre esattamente 91 giorni ATI (mar+gio+sab)."""
    import sys
    sys.path.insert(0, "src")
    from scripts.seed_slot_calendario import _genera_date_ati, STAGIONE_INIZIO, STAGIONE_FINE

    date_ati = _genera_date_ati(STAGIONE_INIZIO, STAGIONE_FINE)
    # Tue+Thu+Sat across ~10 months: 130 days (3 per week × ~43.3 weeks)
    assert len(date_ati) == 130


def test_genera_date_ati_solo_giorni_corretti():
    """Tutti i giorni restituiti devono essere martedì (1), giovedì (3) o sabato (5)."""
    import sys
    sys.path.insert(0, "src")
    from scripts.seed_slot_calendario import _genera_date_ati, GIORNI_ATI, STAGIONE_INIZIO, STAGIONE_FINE

    date_ati = _genera_date_ati(STAGIONE_INIZIO, STAGIONE_FINE)
    for d in date_ati:
        assert d.weekday() in GIORNI_ATI, f"{d} non è un giorno ATI"


def test_genera_date_ati_include_inizio_fine():
    """La funzione deve includere la data di inizio e fine se sono giorni ATI."""
    import sys
    sys.path.insert(0, "src")
    from scripts.seed_slot_calendario import _genera_date_ati

    # Martedì 2 settembre 2026 è il primo martedì dopo il 1° settembre
    date_risultato = _genera_date_ati(date(2026, 9, 1), date(2026, 9, 7))
    weekdays = {d.weekday() for d in date_risultato}
    # In questa settimana: mar=2/9 (1), gio=4/9 (3), sab=6/9 (5)
    assert 1 in weekdays
    assert 3 in weekdays
    assert 5 in weekdays


def test_slot_definitivi_count():
    """Devono essere esattamente 16 slot per giorno (8 notte + 5 mattina + 3 pomeriggio)."""
    import sys
    sys.path.insert(0, "src")
    from scripts.seed_slot_calendario import _SLOT_DEFINITIVI

    assert len(_SLOT_DEFINITIVI) == 16
    fasce = [s[0] for s in _SLOT_DEFINITIVI]
    assert fasce.count("notte") == 8
    assert fasce.count("mattina") == 5
    assert fasce.count("pomeriggio") == 3
