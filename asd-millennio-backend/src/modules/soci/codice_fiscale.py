"""
Validazione formale del codice fiscale italiano (16 caratteri, char di controllo).

Non verifica l'identità della persona (quello lo fa lo staff confrontando col
documento caricato): controlla solo che il CF sia formalmente ben formato.
"""
import re

_ODD = {
    "0": 1, "1": 0, "2": 5, "3": 7, "4": 9, "5": 13, "6": 15, "7": 17, "8": 19, "9": 21,
    "A": 1, "B": 0, "C": 5, "D": 7, "E": 9, "F": 13, "G": 15, "H": 17, "I": 19, "J": 21,
    "K": 2, "L": 4, "M": 18, "N": 20, "O": 11, "P": 3, "Q": 6, "R": 8, "S": 12, "T": 14,
    "U": 16, "V": 10, "W": 22, "X": 25, "Y": 24, "Z": 23,
}
_EVEN = {
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7, "I": 8, "J": 9,
    "K": 10, "L": 11, "M": 12, "N": 13, "O": 14, "P": 15, "Q": 16, "R": 17, "S": 18,
    "T": 19, "U": 20, "V": 21, "W": 22, "X": 23, "Y": 24, "Z": 25,
}
_PATTERN = re.compile(r"^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$")


def cf_valido(cf: str) -> bool:
    """True se il CF è formalmente valido (pattern + carattere di controllo)."""
    if not cf:
        return False
    cf = cf.upper().strip()
    if not _PATTERN.match(cf):
        return False
    somma = 0
    for i, ch in enumerate(cf[:15]):
        somma += _ODD[ch] if (i % 2 == 0) else _EVEN[ch]  # posizioni 1-based dispari = indice pari
    atteso = chr(ord("A") + somma % 26)
    return atteso == cf[15]
