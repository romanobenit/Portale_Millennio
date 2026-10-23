from datetime import date, datetime, time
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from modules.eventi.service import (
    TZ,
    calcola_posti,
    fine_abilitazione,
    fine_evento,
    motivo_non_abilitato,
    scadenza_annullamento,
    solo_online,
)
from schemas.eventi import EventoCreate, EventoUpdate, SegnaPresenzaRequest


def _evento(**kw):
    base = dict(
        data=date(2026, 11, 5),
        ora_inizio=time(18, 30),
        ora_fine=time(20, 30),
        posti_max=10,
        presenze_manuali=0,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _c(online=0, in_sede=0, lock=0, attesa=0):
    return {"online": online, "in_sede": in_sede, "lock": lock, "attesa": attesa}


def test_posti_conta_confermati_e_manuali():
    partecipanti, liberi = calcola_posti(_evento(presenze_manuali=2), _c(online=3, in_sede=1))
    assert partecipanti == 6
    assert liberi == 4


def test_checkout_in_corso_occupa_posto_ma_non_e_partecipante():
    partecipanti, liberi = calcola_posti(_evento(posti_max=4), _c(online=2, lock=2))
    assert partecipanti == 2
    assert liberi == 0


def test_posti_liberi_mai_negativi():
    _, liberi = calcola_posti(_evento(posti_max=3, presenze_manuali=5), _c(in_sede=1))
    assert liberi == 0


def test_annullamento_fino_alla_mezzanotte_del_giorno_prima():
    ev = _evento()
    assert scadenza_annullamento(ev) == datetime(2026, 11, 5, 0, 0, tzinfo=TZ)
    assert fine_evento(ev) == datetime(2026, 11, 5, 20, 30, tzinfo=TZ)


def test_blocco_dopo_due_assenze():
    assert not solo_online(0)
    assert not solo_online(1)
    assert solo_online(2)
    assert solo_online(3)


def _payload(**kw):
    p = dict(
        sport=["pickleball"],
        data=date(2026, 11, 5),
        ora_inizio=time(18, 30),
        ora_fine=time(20, 30),
        prezzo_eur=Decimal("8.00"),
        posti_max=16,
    )
    p.update(kw)
    return p


def test_evento_valido_normalizza_sport():
    ev = EventoCreate(**_payload(sport=[" Badminton ", "pickleball", ""]))
    assert ev.sport == ["badminton", "pickleball"]


@pytest.mark.parametrize("sport", [["olley"], [], ["  "]])
def test_evento_sport_non_valido(sport):
    with pytest.raises(ValidationError):
        EventoCreate(**_payload(sport=sport))


def test_evento_orario_invertito():
    with pytest.raises(ValidationError):
        EventoCreate(**_payload(ora_inizio=time(20, 0), ora_fine=time(19, 0)))


def test_evento_posti_e_prezzo_positivi():
    with pytest.raises(ValidationError):
        EventoCreate(**_payload(posti_max=0))
    with pytest.raises(ValidationError):
        EventoCreate(**_payload(prezzo_eur=Decimal("-1")))


def test_update_sport_validato():
    with pytest.raises(ValidationError):
        EventoUpdate(sport=["olley"])
    assert EventoUpdate(posti_max=20).sport is None


def test_segna_distingue_campo_assente_da_null():
    assert "presenza" not in SegnaPresenzaRequest(pagato_in_sede=True).model_fields_set
    assert "presenza" in SegnaPresenzaRequest(presenza=None).model_fields_set


# ── abilitazione ai campi (tessera Millennio o iscrizione community) ──────────

def test_abilitazione_nessuna_tessera():
    assert fine_abilitazione([], []) is None


def test_abilitazione_tessera_millennio_fino_a_scadenza():
    assert fine_abilitazione([("volley", date(2027, 6, 30))], []) == date(2027, 6, 30)


def test_abilitazione_tessera_esterna_senza_iscrizione_non_conta():
    assert fine_abilitazione([], [date(2027, 8, 31)]) is None


def test_abilitazione_community_usa_la_tessera_esterna_piu_lunga():
    fine = fine_abilitazione([("community", None)], [date(2026, 12, 31), date(2027, 8, 31)])
    assert fine == date(2027, 8, 31)


def test_abilitazione_community_senza_tessera_esterna_valida():
    assert fine_abilitazione([("community", None)], []) is None


def test_abilitazione_vince_la_scadenza_piu_lontana():
    fine = fine_abilitazione([("community", None), ("pickleball", date(2027, 6, 30))], [date(2027, 1, 31)])
    assert fine == date(2027, 6, 30)


def test_motivo_non_abilitato():
    assert "tessera Millennio" in motivo_non_abilitato(None)
    assert "31/08/2027" in motivo_non_abilitato(date(2027, 8, 31))
