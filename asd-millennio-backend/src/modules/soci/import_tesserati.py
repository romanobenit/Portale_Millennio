"""
Lettura del file per il tesseramento in sede massivo (dirigenza).
Accetta il CSV come lo salva Excel: separatore ';' o ',', UTF-8 (anche con BOM)
o Windows-1252, date gg/mm/aaaa o aaaa-mm-gg, intestazioni in italiano.
Le colonne non riconosciute (n. tessera federale, nazione, sesso…) sono ignorate.
"""
import csv
import io
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

ALIAS = {
    "cognome": "cognome",
    "nome": "nome",
    "data_nascita": "data_nascita",
    "data_di_nascita": "data_nascita",
    "nascita": "data_nascita",
    "codice_fiscale": "codice_fiscale",
    "cf": "codice_fiscale",
    "email": "email",
    "e_mail": "email",
    "mail": "email",
    "telefono": "telefono",
    "cellulare": "telefono",
    "indirizzo": "indirizzo",
}
OBBLIGATORIE = ("cognome", "nome", "data_nascita", "codice_fiscale", "email")
MAX_RIGHE = 500


@dataclass
class RigaImport:
    riga: int
    valori: dict = field(default_factory=dict)
    errore: str | None = None


def _chiave(intestazione: str) -> str:
    s = unicodedata.normalize("NFKD", intestazione).encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() else "_" for c in s.strip().lower())
    return "_".join(p for p in s.split("_") if p)


def _decodifica(content: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Codifica del file non riconosciuta: salvalo come CSV (UTF-8).")


def _data(valore: str) -> date:
    v = valore.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"data di nascita non valida: «{v}»")


def leggi_file(content: bytes) -> list[RigaImport]:
    testo = _decodifica(content)
    righe_testo = testo.splitlines()
    if not righe_testo:
        raise ValueError("Il file è vuoto.")
    prima = righe_testo[0]
    separatore = ";" if prima.count(";") >= prima.count(",") else ","
    reader = csv.reader(io.StringIO(testo), delimiter=separatore)
    intestazioni = next(reader, [])
    colonne = [ALIAS.get(_chiave(h)) for h in intestazioni]
    mancanti = [c for c in OBBLIGATORIE if c not in colonne]
    if mancanti:
        raise ValueError("Colonne mancanti nel file: " + ", ".join(mancanti).replace("_", " ") + ".")

    out: list[RigaImport] = []
    for n, valori in enumerate(reader, start=2):
        if not any(v.strip() for v in valori):
            continue
        if len(out) >= MAX_RIGHE:
            raise ValueError(f"Troppe righe: massimo {MAX_RIGHE} per file.")
        r = RigaImport(riga=n)
        for col, v in zip(colonne, valori):
            if col and v.strip():
                r.valori[col] = v.strip()
        vuote = [c for c in OBBLIGATORIE if not r.valori.get(c)]
        if vuote:
            r.errore = "manca: " + ", ".join(vuote).replace("_", " ")
        else:
            try:
                r.valori["data_nascita"] = _data(r.valori["data_nascita"])
                r.valori["codice_fiscale"] = r.valori["codice_fiscale"].upper().replace(" ", "")
                r.valori["email"] = r.valori["email"].lower()
            except ValueError as e:
                r.errore = str(e)
        out.append(r)
    if not out:
        raise ValueError("Nessuna riga da importare nel file.")

    visti_cf: dict[str, int] = {}
    visti_email: dict[str, int] = {}
    for r in out:
        if r.errore:
            continue
        cf, em = r.valori["codice_fiscale"], r.valori["email"]
        if cf in visti_cf:
            r.errore = f"codice fiscale ripetuto (già alla riga {visti_cf[cf]})"
        elif em in visti_email:
            r.errore = f"email ripetuta (già alla riga {visti_email[em]})"
        else:
            visti_cf[cf], visti_email[em] = r.riga, r.riga
    return out
