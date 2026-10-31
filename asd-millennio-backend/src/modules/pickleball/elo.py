"""
Elo interno del club per il pickleball. Non è DUPR (proprietario): è la classifica
della Millennio, calcolata solo dalle partite confermate sul portale.

- Si parte da 1200; nelle prime 10 partite il fattore K è più alto (punteggio provvisorio).
- Doppio: conta la media della coppia, ed entrambi i giocatori ricevono la variazione.
- Conta solo vittoria/sconfitta, non il margine.
- Le partite di torneo pesano di più delle amichevoli (`peso` moltiplica il fattore K).
"""

RATING_INIZIALE = 1200.0
PARTITE_PROVVISORIE = 10
K_PROVVISORIO = 40
K_STANDARD = 24


def fattore_k(partite_giocate: int) -> int:
    return K_PROVVISORIO if partite_giocate < PARTITE_PROVVISORIE else K_STANDARD


def atteso(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def applica_partita(
    stato: dict, squadra_a: list, squadra_b: list, vincitore: str, peso: float = 1.0
) -> dict:
    """
    Aggiorna `stato` (socio -> {"rating", "partite"}) e ritorna socio -> (prima, dopo).
    I giocatori mai visti partono da RATING_INIZIALE.
    """
    for g in squadra_a + squadra_b:
        stato.setdefault(g, {"rating": RATING_INIZIALE, "partite": 0})
    media_a = sum(stato[g]["rating"] for g in squadra_a) / len(squadra_a)
    media_b = sum(stato[g]["rating"] for g in squadra_b) / len(squadra_b)
    e_a = atteso(media_a, media_b)
    s_a = 1.0 if vincitore == "a" else 0.0

    variazioni = {}
    for squadra, risultato in ((squadra_a, s_a - e_a), (squadra_b, (1 - s_a) - (1 - e_a))):
        for g in squadra:
            prima = stato[g]["rating"]
            dopo = round(prima + fattore_k(stato[g]["partite"]) * peso * risultato, 2)
            variazioni[g] = (round(prima, 2), dopo)
    for g, (_, dopo) in variazioni.items():
        stato[g]["rating"] = dopo
        stato[g]["partite"] += 1
    return variazioni


def vincitore_da_punteggi(punteggi: list) -> str:
    """
    Valida i game ([[11, 7], [9, 11], ...], punti squadra A / squadra B) e ritorna "a" o "b".
    Ogni game: si vince ad almeno 11 con 2 punti di scarto (vale anche per game a 15 o 21).
    """
    if not isinstance(punteggi, list) or not 1 <= len(punteggi) <= 5:
        raise ValueError("Indica da 1 a 5 game.")
    vinti_a = vinti_b = 0
    for i, game in enumerate(punteggi, start=1):
        if not (isinstance(game, (list, tuple)) and len(game) == 2
                and all(isinstance(p, int) and 0 <= p <= 99 for p in game)):
            raise ValueError(f"Game {i}: punteggio non valido.")
        a, b = game
        if max(a, b) < 11 or abs(a - b) < 2:
            raise ValueError(f"Game {i} ({a}-{b}): si vince ad almeno 11 con 2 punti di scarto.")
        if a > b:
            vinti_a += 1
        else:
            vinti_b += 1
    if vinti_a == vinti_b:
        raise ValueError("La partita non può finire in parità: controlla i game.")
    return "a" if vinti_a > vinti_b else "b"
