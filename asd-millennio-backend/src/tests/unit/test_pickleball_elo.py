import pytest

from modules.pickleball.elo import (
    K_PROVVISORIO,
    K_STANDARD,
    RATING_INIZIALE,
    applica_partita,
    atteso,
    fattore_k,
    vincitore_da_punteggi,
)


def test_atteso_simmetrico():
    assert atteso(1200, 1200) == pytest.approx(0.5)
    assert atteso(1400, 1200) + atteso(1200, 1400) == pytest.approx(1)


def test_fattore_k_provvisorio():
    assert fattore_k(0) == K_PROVVISORIO
    assert fattore_k(9) == K_PROVVISORIO
    assert fattore_k(10) == K_STANDARD


def test_singolo_parita_di_rating_vince_a():
    stato = {}
    v = applica_partita(stato, ["anna"], ["bea"], "a")
    assert v["anna"] == (RATING_INIZIALE, RATING_INIZIALE + K_PROVVISORIO / 2)
    assert v["bea"] == (RATING_INIZIALE, RATING_INIZIALE - K_PROVVISORIO / 2)
    assert stato["anna"]["partite"] == 1


def test_somma_zero_con_stesso_k():
    stato = {"a": {"rating": 1300, "partite": 20}, "b": {"rating": 1100, "partite": 20}}
    v = applica_partita(stato, ["a"], ["b"], "b")
    guadagno_b = v["b"][1] - v["b"][0]
    perdita_a = v["a"][0] - v["a"][1]
    assert guadagno_b == pytest.approx(perdita_a, abs=0.01)
    assert guadagno_b > K_STANDARD / 2  # sorpresa: il più debole guadagna più della metà di K


def test_doppio_usa_la_media_e_aggiorna_entrambi():
    stato = {"a1": {"rating": 1400, "partite": 20}, "a2": {"rating": 1000, "partite": 20},
             "b1": {"rating": 1200, "partite": 20}, "b2": {"rating": 1200, "partite": 20}}
    v = applica_partita(stato, ["a1", "a2"], ["b1", "b2"], "a")
    # medie uguali (1200) → atteso 0.5 → +12 a entrambi i vincitori
    assert v["a1"][1] - v["a1"][0] == pytest.approx(12)
    assert v["a2"][1] - v["a2"][0] == pytest.approx(12)
    assert v["b1"][1] - v["b1"][0] == pytest.approx(-12)


@pytest.mark.parametrize("punteggi,vincitore", [
    ([[11, 7]], "a"),
    ([[9, 11], [11, 5], [11, 9]], "a"),
    ([[13, 15], [8, 11]], "b"),
    ([[21, 19]], "a"),
])
def test_punteggi_validi(punteggi, vincitore):
    assert vincitore_da_punteggi(punteggi) == vincitore


@pytest.mark.parametrize("punteggi", [
    [], [[11, 10]], [[10, 8]], [[11, 7], [7, 11]], [[11, "x"]], [[11, 7]] * 6, "11-7",
])
def test_punteggi_non_validi(punteggi):
    with pytest.raises(ValueError):
        vincitore_da_punteggi(punteggi)
