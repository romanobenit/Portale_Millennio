"""
Regole di classifica e circuito pickleball, senza accesso al database.

- Impostazioni predefinite (la dirigenza le può cambiare: `config_pickleball`).
- Sesso e fascia d'età ricavati da codice fiscale e data di nascita: nessun dato in più ai soci.
- Piazzamenti di un torneo ricavati dalle partite della categoria.
"""
from copy import deepcopy
from datetime import date

CONFIG_DEFAULT: dict = {
    "peso_torneo": 1.5,              # moltiplica il fattore K nelle partite di torneo
    "amichevoli_max_settimana": 3,   # amichevoli contate per settimana contro lo stesso avversario
    "giorni_inattivita": 90,         # oltre, si esce dalla classifica dei soci (resta lo storico)
    "migliori_risultati": 6,         # tornei che contano nel circuito di una stagione
    "punti": {"vincitore": 100, "finalista": 70, "semifinalista": 45, "fase_finale": 25, "partecipazione": 10},
    "livelli": {"sociale": 1.0, "open": 1.5, "federale": 2.0},
}

ORDINE_PIAZZAMENTI = ("nessuno", "partecipazione", "fase_finale", "semifinalista", "finalista", "vincitore")
_OMOCODIA = {c: str(i) for i, c in enumerate("LMNPQRSTUV")}


def config_completa(valori: dict | None) -> dict:
    """Impostazioni salvate sopra i valori predefiniti (le chiavi mancanti restano di default)."""
    cfg = deepcopy(CONFIG_DEFAULT)
    for k, v in (valori or {}).items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        elif k in cfg:
            cfg[k] = v
    return cfg


def sesso_da_cf(cf: str | None) -> str | None:
    """Il giorno di nascita nel codice fiscale vale +40 per le donne (gestisce l'omocodia)."""
    if not cf or len(cf) < 11:
        return None
    giorno = "".join(_OMOCODIA.get(c, c) for c in cf[9:11].upper())
    if not giorno.isdigit():
        return None
    return "F" if int(giorno) > 40 else "M"


def eta_nell_anno(data_nascita: date | None, anno: int) -> int | None:
    """Età compiuta entro l'anno (come per le categorie per età: conta l'anno di nascita)."""
    return anno - data_nascita.year if data_nascita else None


def anno_sportivo_di(d: date) -> str:
    """L'anno sportivo va da luglio a giugno, come le tessere (scadenza 30 giugno)."""
    return f"{d.year}-{d.year + 1}" if d.month >= 7 else f"{d.year - 1}-{d.year}"


def migliore(a: str | None, b: str | None) -> str | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if ORDINE_PIAZZAMENTI.index(a) >= ORDINE_PIAZZAMENTI.index(b) else b


def piazzamenti_categoria(partite: list[dict]) -> dict:
    """
    partite: [{"fase", "a": [giocatori], "b": [giocatori], "vincitore": "a"|"b", "walkover": bool}]
    Ritorna giocatore -> piazzamento. È presente solo chi ha giocato almeno una partita o ne ha
    vinta una a tavolino: chi ha solo dato forfait non prende punti. Il walkover vale come turno superato.
    """
    presenti: set = set()
    for p in partite:
        vincenti = p[p["vincitore"]]
        perdenti = p["b" if p["vincitore"] == "a" else "a"]
        presenti.update(vincenti)
        if not p.get("walkover"):
            presenti.update(perdenti)

    esito: dict = {}

    def assegna(giocatori, piazzamento):
        for g in giocatori:
            if g in presenti:
                esito[g] = migliore(esito.get(g), piazzamento)

    if not any((p.get("fase") or "girone") != "girone" for p in partite):
        # Girone unico (nessun tabellone): conta la classifica del girone
        for squadra, piazzamento in classifica_girone(partite, presenti).items():
            assegna(squadra, piazzamento)
        return esito

    for p in partite:
        vincenti = p[p["vincitore"]]
        perdenti = p["b" if p["vincitore"] == "a" else "a"]
        fase = p.get("fase") or "girone"
        if fase == "finale":
            assegna(vincenti, "vincitore")
            assegna(perdenti, "finalista")
        elif fase == "semifinale":
            assegna(vincenti, "semifinalista")
            assegna(perdenti, "semifinalista")
        elif fase in ("quarti", "ottavi"):
            assegna(vincenti, "fase_finale")
            assegna(perdenti, "fase_finale")
        else:
            assegna(vincenti + perdenti, "partecipazione")
    return esito


PIAZZAMENTI_GIRONE = ("vincitore", "finalista", "semifinalista", "semifinalista")


def classifica_girone(partite: list[dict], presenti: set | None = None) -> dict:
    """
    Girone all'italiana: squadre ordinate per vittorie (anche a tavolino), poi differenza punti.
    1° vincitore, 2° finalista, 3° e 4° semifinalisti, gli altri partecipazione; a pari merito
    si condivide il piazzamento migliore. Chi non si è presentato non occupa posizioni.
    Ritorna squadra (tuple di giocatori) -> piazzamento.
    """
    vittorie: dict = {}
    differenza: dict = {}
    for p in partite:
        for lato in ("a", "b"):
            squadra = tuple(sorted(p[lato], key=str))
            if squadra:
                vittorie.setdefault(squadra, 0)
                differenza.setdefault(squadra, 0)
        vincenti = tuple(sorted(p[p["vincitore"]], key=str))
        vittorie[vincenti] = vittorie.get(vincenti, 0) + 1
        for game in p.get("punteggi") or []:
            for lato, segno in (("a", 1), ("b", -1)):
                squadra = tuple(sorted(p[lato], key=str))
                if squadra:
                    differenza[squadra] = differenza.get(squadra, 0) + segno * (game[0] - game[1])
    squadre = [s for s in vittorie if presenti is None or all(g in presenti for g in s)]
    ordinate = sorted(squadre, key=lambda s: (-vittorie[s], -differenza[s]))
    esito = {}
    for i, squadra in enumerate(ordinate):
        pari = next(
            j for j, altra in enumerate(ordinate)
            if (vittorie[altra], differenza[altra]) == (vittorie[squadra], differenza[squadra])
        )
        esito[squadra] = PIAZZAMENTI_GIRONE[pari] if pari < len(PIAZZAMENTI_GIRONE) else "partecipazione"
    return esito


def punti_piazzamento(piazzamento: str, livello: str, cfg: dict) -> float:
    return round(cfg["punti"].get(piazzamento, 0) * cfg["livelli"].get(livello, 1.0), 1)
