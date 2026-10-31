from datetime import date

import pytest

from modules.pickleball import import_risultati
from modules.pickleball.regole import (
    anno_sportivo_di,
    classifica_girone,
    config_completa,
    piazzamenti_categoria,
    punti_piazzamento,
    sesso_da_cf,
)


def test_config_completa_unisce_i_default():
    cfg = config_completa({"peso_torneo": 2, "punti": {"vincitore": 120}})
    assert cfg["peso_torneo"] == 2
    assert cfg["punti"]["vincitore"] == 120
    assert cfg["punti"]["finalista"] == 70
    assert cfg["livelli"]["open"] == 1.5


@pytest.mark.parametrize("cf,sesso", [
    ("RSSMRA80A01F839X", "M"),
    ("RSSMRA80A41F839X", "F"),
    ("RSSMRA80A4MF839X", "F"),   # omocodia: M = 1
    ("RSSMRA80ALMF839X", "M"),   # omocodia: L = 0, M = 1 → 01
    ("CORTO", None),
])
def test_sesso_da_codice_fiscale(cf, sesso):
    assert sesso_da_cf(cf) == sesso


def test_anno_sportivo():
    assert anno_sportivo_di(date(2026, 10, 18)) == "2026-2027"
    assert anno_sportivo_di(date(2027, 6, 30)) == "2026-2027"
    assert anno_sportivo_di(date(2027, 7, 1)) == "2027-2028"


def p(fase, a, b, vincitore, walkover=False, punteggi=None):
    return {"fase": fase, "a": a, "b": b, "vincitore": vincitore, "walkover": walkover, "punteggi": punteggi or []}


def test_piazzamenti_tabellone_e_forfait():
    # Torneo reale SMO40: chi ha solo dato forfait non prende nulla
    partite = [
        p("girone", ["sanna"], ["stradi"], "b", punteggi=[[8, 11]]),
        p("girone", ["riccio"], ["gambardella"], "b", punteggi=[[9, 11]]),
        p("girone", ["bozzaotre"], ["di_trani"], "a", walkover=True),
        p("girone", ["bitetti"], ["sanna"], "b", walkover=True),
        p("semifinale", ["stradi"], ["pallavanti"], "a", punteggi=[[11, 5]]),
        p("semifinale", ["bozzaotre"], ["gambardella"], "a", punteggi=[[11, 3]]),
        p("finale", ["stradi"], ["bozzaotre"], "b", punteggi=[[3, 15]]),
    ]
    esito = piazzamenti_categoria(partite)
    assert esito["bozzaotre"] == "vincitore"
    assert esito["stradi"] == "finalista"
    assert esito["pallavanti"] == esito["gambardella"] == "semifinalista"
    assert esito["sanna"] == esito["riccio"] == "partecipazione"
    assert "bitetti" not in esito and "di_trani" not in esito


def test_piazzamenti_doppio_con_semifinali_a_tavolino():
    partite = [
        p("semifinale", ["boz", "vac"], [], "a", walkover=True),
        p("semifinale", [], ["eri", "gri"], "b", walkover=True),
        p("finale", ["boz", "vac"], ["eri", "gri"], "a", punteggi=[[15, 2]]),
    ]
    esito = piazzamenti_categoria(partite)
    assert esito == {"boz": "vincitore", "vac": "vincitore", "eri": "finalista", "gri": "finalista"}


def test_girone_unico_classifica_per_vittorie_e_differenza():
    # Torneo reale DMO40 (girone all'italiana, nessun tabellone)
    gl, ss, pr, gn, bd = ("gam", "lam"), ("san", "str"), ("pal", "rom"), ("gio", "nuz"), ("bru", "dit")
    partite = [
        p("girone", list(ss), list(gl), "b", punteggi=[[9, 11]]),
        p("girone", list(pr), list(gn), "a", walkover=True),
        p("girone", list(ss), list(bd), "a", walkover=True),
        p("girone", list(pr), list(ss), "b", punteggi=[[8, 11]]),
        p("girone", list(gl), list(bd), "a", walkover=True),
        p("girone", list(gn), list(ss), "b", walkover=True),
        p("girone", list(pr), list(gl), "b", punteggi=[[8, 11]]),
        p("girone", list(gn), list(gl), "b", walkover=True),
        p("girone", list(pr), list(bd), "a", walkover=True),
    ]
    esito = piazzamenti_categoria(partite)
    assert esito["gam"] == esito["lam"] == "vincitore"
    assert esito["san"] == "finalista"
    assert esito["pal"] == "semifinalista"
    assert "gio" not in esito and "bru" not in esito


def test_girone_pari_merito_condivide_il_piazzamento():
    partite = [p("girone", ["a"], ["b"], "a", punteggi=[[11, 5]]), p("girone", ["b"], ["c"], "a", punteggi=[[11, 5]]),
               p("girone", ["c"], ["a"], "a", punteggi=[[11, 5]])]
    esito = classifica_girone(partite)
    assert set(esito.values()) == {"vincitore"}


def test_punti_con_livello():
    cfg = config_completa(None)
    assert punti_piazzamento("vincitore", "sociale", cfg) == 100
    assert punti_piazzamento("finalista", "open", cfg) == 105
    assert punti_piazzamento("nessuno", "federale", cfg) == 0


CSV = (
    "categoria;fase;squadra_a;squadra_b;punteggio;vincitore\n"
    "SMO40;Group A;Riccardo Sanna;Roberto Stradi [1];8-11;\n"
    "DMO15;semi final;Michele Bozzaotre / Michele Vaccaro;;WO;A\n"
    "SFO15;girone;Mirella Zeverino;Ines Direnzo;annullata;\n"
    "SMO40;finale;Roberto Stradi;Michele Bozzaotre;3-15;A\n"
    "SMO40;girone;Uno;Due / Tre;11-5;\n"
    "SMO40;girone;Uno;Due;WO;\n"
    "SMO40;girone;Uno;Due;11-10;\n"
).encode("utf-8")


def test_lettura_file_risultati():
    righe = import_risultati.leggi_file(CSV)
    r = {x.riga: x for x in righe}
    assert r[2].fase == "girone" and r[2].vincitore == "b" and r[2].punteggi == [[8, 11]]
    assert r[2].squadra_b == ["Roberto Stradi [1]"]
    assert r[3].fase == "semifinale" and r[3].walkover and r[3].vincitore == "a" and r[3].squadra_b == []
    assert r[4].saltata
    assert r[5].errore == "il vincitore indicato non corrisponde al punteggio"
    assert "1 giocatore" in r[6].errore
    assert "indica il vincitore" in r[7].errore
    assert "2 punti di scarto" in r[8].errore


def test_normalizza_nome():
    assert import_risultati.normalizza_nome("  Roberto  STRADI [1] ") == "roberto stradi"
    assert import_risultati.normalizza_nome("Niccolò D'Amico") == "niccolo damico"


def test_colonne_mancanti():
    with pytest.raises(ValueError, match="Colonne mancanti"):
        import_risultati.leggi_file(b"categoria;squadra_a\nX;Y\n")
