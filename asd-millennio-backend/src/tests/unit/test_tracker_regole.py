from datetime import date
from decimal import Decimal

from modules.tracker.regole import (
    SPORT,
    ContattoConteggio,
    conteggia,
    costo_periodo,
    mesi,
    normalizza_nome,
    stesso_nome,
)


def c(sport, stato, storico=(), importo=None):
    return ContattoConteggio(
        sport=sport, stato=stato, stati_raggiunti=set(storico) | {stato},
        importo_eur=None if importo is None else Decimal(importo),
    )


def test_una_riga_per_ogni_sport_anche_vuota():
    righe = conteggia([])
    assert list(righe) == list(SPORT)
    assert all(r.lead == 0 and r.conversione_pct is None for r in righe.values())


def test_imbuto_conta_le_fasi_raggiunte():
    righe = conteggia([
        c("badminton", "lead"),
        c("badminton", "prova_prenotata", ["lead"]),
        c("badminton", "pagato", ["lead", "prova_prenotata", "prova_svolta", "iscritto"], "50"),
        c("badminton", "perso", ["lead", "prova_prenotata", "prova_svolta"]),
    ])
    r = righe["badminton"]
    assert (r.lead, r.prove_prenotate, r.prove_svolte, r.iscritti, r.paganti, r.persi) == (4, 3, 2, 1, 1, 1)
    assert r.conversione_pct == Decimal("25.0")
    assert r.incassato_eur == Decimal("50")


def test_prova_svolta_senza_prenotata_conta_anche_come_prenotata():
    r = conteggia([c("pallavolo", "prova_svolta", ["lead"])])["pallavolo"]
    assert (r.prove_prenotate, r.prove_svolte) == (1, 1)


def test_pagato_diretto_non_inventa_la_prova():
    # Chi si iscrive e paga subito (passaggio in struttura) non ha fatto la prova.
    r = conteggia([c("kung_fu", "pagato", ["lead"], "40")])["kung_fu"]
    assert (r.prove_prenotate, r.prove_svolte, r.iscritti, r.paganti) == (0, 0, 1, 1)


def test_incassato_e_impegnato_separati():
    righe = conteggia([
        c("pickleball", "iscritto", ["lead"], "30"),            # impegnato
        c("pickleball", "pagato", ["lead", "iscritto"], "30"),  # incassato
        c("pickleball", "perso", ["lead", "iscritto"], "30"),   # iscritto ma perso: né l'uno né l'altro
    ])
    r = righe["pickleball"]
    assert r.incassato_eur == Decimal("30")
    assert r.impegnato_eur == Decimal("30")
    assert r.iscritti == 3 and r.paganti == 1 and r.persi == 1


def test_pagato_poi_perso_resta_incassato():
    r = conteggia([c("badminton", "perso", ["lead", "pagato"], "20")])["badminton"]
    assert r.paganti == 1 and r.incassato_eur == Decimal("20")


def test_importo_mancante_vale_zero():
    r = conteggia([c("calcio_a_5", "pagato", ["lead"])])["calcio_a_5"]
    assert r.paganti == 1 and r.incassato_eur == Decimal("0.00")


def test_conversione_arrotondata():
    righe = conteggia([c("badminton", "pagato", ["lead"])] + [c("badminton", "lead") for _ in range(2)])
    assert righe["badminton"].conversione_pct == Decimal("33.3")


def test_mesi_attraversa_l_anno():
    assert mesi(date(2026, 11, 20), date(2027, 2, 3)) == [
        date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1), date(2027, 2, 1),
    ]


def test_costo_periodo_usa_la_variazione_in_vigore():
    costi = [(date(2026, 10, 1), Decimal("300")), (date(2027, 1, 1), Decimal("400"))]
    # nov, dic a 300; gen, feb a 400
    assert costo_periodo(costi, date(2026, 11, 15), date(2027, 2, 10)) == Decimal("1400")


def test_costo_periodo_prima_della_prima_variazione_e_zero():
    costi = [(date(2027, 1, 1), Decimal("400"))]
    assert costo_periodo(costi, date(2026, 11, 1), date(2027, 1, 31)) == Decimal("400")
    assert costo_periodo([], date(2026, 11, 1), date(2027, 1, 31)) == Decimal("0.00")


def test_stesso_nome_ignora_ordine_maiuscole_accenti_spazi():
    assert stesso_nome("Mario  Rossi", "rossi mario")
    assert stesso_nome("Niccolò Esposito", "niccolo esposito")
    assert not stesso_nome("Mario Rossi", "Maria Rossi")
    assert normalizza_nome("  Àndrea   DE  Luca ") == "andrea de luca"
