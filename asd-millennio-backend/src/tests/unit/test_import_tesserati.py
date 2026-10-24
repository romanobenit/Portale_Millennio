from datetime import date

import pytest

from modules.soci.import_tesserati import leggi_file


def test_csv_excel_italiano_punto_e_virgola_e_colonne_extra():
    testo = (
        "N. Tessera;Cognome;Nome;Nazione;Sesso;Data di Nascita;Codice Fiscale;E-mail\n"
        "402542;Bozzaotre;Michele;Italy;M;24/09/1975;bzzmhl75p24f839x;MICHELE@ESEMPIO.IT\n"
    )
    righe = leggi_file(testo.encode("cp1252"))
    assert len(righe) == 1
    r = righe[0]
    assert r.errore is None
    assert r.valori["data_nascita"] == date(1975, 9, 24)
    assert r.valori["codice_fiscale"] == "BZZMHL75P24F839X"
    assert r.valori["email"] == "michele@esempio.it"
    assert "nazione" not in r.valori


def test_csv_virgola_utf8_con_bom_e_date_iso():
    testo = "cognome,nome,data_nascita,codice_fiscale,email\nRossi,Mario,1980-01-31,RSSMRA80A31H501X,m@r.it\n"
    righe = leggi_file(testo.encode("utf-8-sig"))
    assert righe[0].valori["data_nascita"] == date(1980, 1, 31)


def test_colonne_obbligatorie_mancanti():
    with pytest.raises(ValueError, match="codice fiscale"):
        leggi_file(b"Cognome;Nome;Data di nascita;Email\nRossi;Mario;01/01/1980;m@r.it\n")


def test_riga_incompleta_e_data_errata_segnalate_per_riga():
    testo = (
        "Cognome;Nome;Data di nascita;CF;Email\n"
        "Rossi;Mario;31/02/1980;RSSMRA80A01H501X;m@r.it\n"
        "Bianchi;Anna;01/01/1980;;a@b.it\n"
        "\n"
    )
    righe = leggi_file(testo.encode())
    assert len(righe) == 2
    assert "data di nascita non valida" in righe[0].errore
    assert "codice fiscale" in righe[1].errore


def test_duplicati_nel_file():
    testo = (
        "Cognome;Nome;Data di nascita;CF;Email\n"
        "Rossi;Mario;01/01/1980;RSSMRA80A01H501X;m@r.it\n"
        "Rossi;Mario;01/01/1980;rssmra80a01h501x;altra@r.it\n"
        "Verdi;Luca;01/01/1981;VRDLCU81A01H501X;M@R.IT\n"
    )
    righe = leggi_file(testo.encode())
    assert righe[0].errore is None
    assert "codice fiscale ripetuto" in righe[1].errore
    assert "email ripetuta" in righe[2].errore


def test_file_vuoto():
    with pytest.raises(ValueError):
        leggi_file(b"")
