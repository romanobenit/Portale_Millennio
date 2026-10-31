"""
Lettura del file dei risultati di un torneo (dirigenza).

Una riga per partita, CSV come lo salva Excel (';' o ',', UTF-8 o Windows-1252):

    categoria;fase;squadra_a;squadra_b;punteggio;vincitore
    SMO40;girone;Riccardo Sanna;Roberto Stradi;8-11;
    DMO15;finale;Michele Bozzaotre / Michele Vaccaro;Ernesto Riccio / Gaetano Riccio;15-2;
    SMO40;girone;Michele Bozzaotre;Giuseppe Di Trani;WO;A

- I giocatori di una coppia si separano con "/"; i nomi sono "Nome Cognome".
- Il punteggio è dal punto di vista della squadra A ("11-8" o "11-8, 9-11, 11-6").
- Walkover: punteggio "WO" (o "walkover") e vincitore A o B obbligatorio; la squadra assente
  può restare vuota. Le partite annullate ("annullata", "cancelled" o punteggio vuoto) si saltano.
"""
import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field

from modules.pickleball.elo import vincitore_da_punteggi
from modules.soci.import_tesserati import _chiave, _decodifica

ALIAS = {
    "categoria": "categoria",
    "evento": "categoria",
    "event": "categoria",
    "fase": "fase",
    "turno": "fase",
    "round": "fase",
    "squadra_a": "squadra_a",
    "giocatore_a": "squadra_a",
    "giocatori_a": "squadra_a",
    "squadra_b": "squadra_b",
    "giocatore_b": "squadra_b",
    "giocatori_b": "squadra_b",
    "punteggio": "punteggio",
    "risultato": "punteggio",
    "score": "punteggio",
    "vincitore": "vincitore",
    "winner": "vincitore",
}
OBBLIGATORIE = ("categoria", "squadra_a", "squadra_b", "punteggio")
MAX_RIGHE = 500

FASI = {
    "finale": "finale", "final": "finale",
    "semifinale": "semifinale", "semifinali": "semifinale", "semi_final": "semifinale", "semi": "semifinale",
    "quarti": "quarti", "quarto": "quarti", "quarter_final": "quarti", "quarti_di_finale": "quarti",
    "ottavi": "ottavi", "ottavi_di_finale": "ottavi", "round_of_16": "ottavi",
}
WALKOVER = {"wo", "w_o", "walkover", "forfait", "ritiro"}
ANNULLATA = {"annullata", "annullato", "cancelled", "canceled", "non_giocata"}


def normalizza_nome(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\[\d+\]", " ", s)          # teste di serie "[1]"
    s = re.sub(r"[^a-z' ]+", " ", s).replace("'", "")
    return " ".join(s.split())


def fase_da_testo(testo: str) -> str:
    k = _chiave(testo or "")
    if not k:
        return "girone"
    return FASI.get(k, "girone")


def _giocatori(testo: str) -> list[str]:
    return [n.strip() for n in re.split(r"[/+]", testo or "") if n.strip()]


def _punteggi(testo: str) -> list[list[int]]:
    games = [g for g in re.split(r"[,;]", testo) if g.strip()]
    out = []
    for g in games:
        m = re.fullmatch(r"\s*(\d{1,2})\s*[-–:]\s*(\d{1,2})\s*", g)
        if not m:
            raise ValueError(f"punteggio non leggibile: «{testo.strip()}»")
        out.append([int(m.group(1)), int(m.group(2))])
    return out


@dataclass
class RigaRisultato:
    riga: int
    categoria: str = ""
    fase: str = "girone"
    squadra_a: list[str] = field(default_factory=list)
    squadra_b: list[str] = field(default_factory=list)
    punteggi: list[list[int]] = field(default_factory=list)
    vincitore: str | None = None
    walkover: bool = False
    saltata: str | None = None
    errore: str | None = None


def leggi_file(content: bytes) -> list[RigaRisultato]:
    testo = _decodifica(content)
    righe_testo = testo.splitlines()
    if not righe_testo:
        raise ValueError("Il file è vuoto.")
    prima = righe_testo[0]
    separatore = ";" if prima.count(";") >= prima.count(",") else ","
    reader = csv.reader(io.StringIO(testo), delimiter=separatore)
    colonne = [ALIAS.get(_chiave(h)) for h in next(reader, [])]
    mancanti = [c for c in OBBLIGATORIE if c not in colonne]
    if mancanti:
        raise ValueError("Colonne mancanti nel file: " + ", ".join(mancanti).replace("_", " ") + ".")

    out: list[RigaRisultato] = []
    for n, valori in enumerate(reader, start=2):
        if not any(v.strip() for v in valori):
            continue
        if len(out) >= MAX_RIGHE:
            raise ValueError(f"Troppe righe: massimo {MAX_RIGHE} per file.")
        v = {col: val.strip() for col, val in zip(colonne, valori) if col}
        r = RigaRisultato(
            riga=n,
            categoria=v.get("categoria", "").upper().replace(" ", "")[:20],
            fase=fase_da_testo(v.get("fase", "")),
            squadra_a=_giocatori(v.get("squadra_a", "")),
            squadra_b=_giocatori(v.get("squadra_b", "")),
        )
        out.append(r)
        punteggio = v.get("punteggio", "")
        vincitore = _chiave(v.get("vincitore", ""))
        if vincitore and vincitore not in ("a", "b"):
            r.errore = "il vincitore va indicato come A o B"
            continue
        if not r.categoria:
            r.errore = "manca la categoria"
            continue
        k = _chiave(punteggio)
        if k in ANNULLATA or (not k and not vincitore):
            r.saltata = "partita non giocata"
            continue
        if k in WALKOVER or (not k and vincitore):
            if not vincitore:
                r.errore = "walkover: indica il vincitore (A o B)"
                continue
            if not (r.squadra_a if vincitore == "a" else r.squadra_b):
                r.errore = "walkover: manca la squadra vincitrice"
                continue
            r.walkover, r.vincitore = True, vincitore
            continue
        if not r.squadra_a or not r.squadra_b:
            r.errore = "mancano i giocatori di una squadra"
            continue
        if len(r.squadra_a) != len(r.squadra_b) or len(r.squadra_a) > 2:
            r.errore = "le squadre devono avere 1 giocatore (singolo) o 2 (doppio) ciascuna"
            continue
        try:
            r.punteggi = _punteggi(punteggio)
            r.vincitore = vincitore_da_punteggi(r.punteggi)
        except ValueError as e:
            r.errore = str(e)
            continue
        if vincitore and vincitore != r.vincitore:
            r.errore = "il vincitore indicato non corrisponde al punteggio"
    if not out:
        raise ValueError("Nessuna riga da importare nel file.")
    return out
