from datetime import date

from modules.soci.gestione_tesseramenti import (
    CATEGORIE_CAMBIABILI,
    _eta,
    motivo_non_eliminabile,
    pulisci_nome,
)


def test_pulisci_nome_toglie_spazi_doppi():
    assert pulisci_nome("  Michele   Vaccaro ") == "Michele Vaccaro"
    assert pulisci_nome("De  Luca") == "De Luca"


def test_eliminabile_solo_senza_pagamenti_contabili():
    assert motivo_non_eliminabile([]) is None
    assert motivo_non_eliminabile(["in_attesa_pagamento"]) is None       # checkout abbandonato
    for stato in ("pagato", "rimborsato", "erogazione_liberale"):
        assert motivo_non_eliminabile(["in_attesa_pagamento", stato]) is not None


def test_community_non_cambiabile():
    assert "community" not in CATEGORIE_CAMBIABILI
    assert {"volley", "badminton", "kung_fu", "pickleball", "sostenitore"} <= CATEGORIE_CAMBIABILI


def test_eta_al_compleanno():
    assert _eta(date(2008, 11, 15), oggi=date(2026, 11, 15)) == 18
    assert _eta(date(2008, 11, 16), oggi=date(2026, 11, 15)) == 17
