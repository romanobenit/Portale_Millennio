"""
Regole del tracker iscritti, senza database: etichette delle tendine, conteggi
dell'imbuto (lead → prova → iscritto → pagato) e costo istruttore di un periodo.

Conteggi: ogni contatto conta per le fasi che ha davvero raggiunto, ricavate dallo
storico degli stati. Così un contatto oggi "pagato" resta fra i lead e fra chi ha
fatto la prova, e uno "perso" resta nelle fasi a cui era arrivato.
"""
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

SPORT = {
    "kung_fu": "Wushu/Kung Fu",
    "pallavolo": "Pallavolo",
    "badminton": "Badminton",
    "pickleball": "Pickleball",
    "tornei_pickleball": "Tornei Pickleball",
    "basket_serale": "Turno basket serale",
    "calcio_a_5": "Calcio a 5",
}
FONTI = {
    "meta_ads": "Meta Ads",
    "organico": "Organico",
    "torneo": "Torneo",
    "passaggio_struttura": "Passaggio in struttura",
    "passaparola": "Passaparola",
    "altro": "Altro",
}
CANALI = {"whatsapp": "WhatsApp", "email": "Email", "instagram": "Instagram"}
STATI = {
    "lead": "Lead",
    "prova_prenotata": "Prova prenotata",
    "prova_svolta": "Prova svolta",
    "iscritto": "Iscritto",
    "pagato": "Pagato",
    "perso": "Perso",
}
ABBONAMENTI = {"mensile": "Mensile", "annuale": "Annuale"}

STATI_CHIUSI = {"pagato", "perso"}     # niente più follow-up


@dataclass
class ContattoConteggio:
    sport: str
    stato: str                  # stato attuale
    stati_raggiunti: set[str]   # tutti gli stati dello storico (compreso quello attuale)
    importo_eur: Decimal | None


@dataclass
class RigaConteggio:
    lead: int = 0
    prove_prenotate: int = 0
    prove_svolte: int = 0
    iscritti: int = 0
    paganti: int = 0
    persi: int = 0
    incassato_eur: Decimal = field(default_factory=lambda: Decimal("0.00"))
    impegnato_eur: Decimal = field(default_factory=lambda: Decimal("0.00"))

    @property
    def conversione_pct(self) -> Decimal | None:
        """Paganti diviso lead, in percentuale con un decimale."""
        if not self.lead:
            return None
        return (Decimal(self.paganti) * 100 / self.lead).quantize(Decimal("0.1"))

    def aggiungi(self, c: ContattoConteggio) -> None:
        raggiunti = c.stati_raggiunti | {c.stato}
        importo = c.importo_eur or Decimal("0.00")
        self.lead += 1
        # Chi ha svolto la prova l'aveva anche prenotata, anche se lo stato è stato saltato.
        if raggiunti & {"prova_prenotata", "prova_svolta"}:
            self.prove_prenotate += 1
        if "prova_svolta" in raggiunti:
            self.prove_svolte += 1
        if raggiunti & {"iscritto", "pagato"}:
            self.iscritti += 1
        if "pagato" in raggiunti:
            self.paganti += 1
            self.incassato_eur += importo
        elif "iscritto" in raggiunti and c.stato != "perso":
            # Iscritto che non ha ancora pagato: quanto si è impegnato a versare.
            self.impegnato_eur += importo
        if c.stato == "perso":
            self.persi += 1

    def somma(self, altra: "RigaConteggio") -> None:
        for campo in ("lead", "prove_prenotate", "prove_svolte", "iscritti", "paganti", "persi"):
            setattr(self, campo, getattr(self, campo) + getattr(altra, campo))
        self.incassato_eur += altra.incassato_eur
        self.impegnato_eur += altra.impegnato_eur


def conteggia(contatti: list[ContattoConteggio]) -> dict[str, RigaConteggio]:
    """Una riga per ogni sport della tendina (anche a zero), nell'ordine della tendina."""
    righe = {s: RigaConteggio() for s in SPORT}
    for c in contatti:
        righe[c.sport].aggiungi(c)
    return righe


def primo_del_mese(d: date) -> date:
    return d.replace(day=1)


def mesi(dal: date, al: date) -> list[date]:
    """Primi giorni dei mesi da `dal` ad `al` compresi."""
    out: list[date] = []
    m = primo_del_mese(dal)
    fine = primo_del_mese(al)
    while m <= fine:
        out.append(m)
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return out


def costo_periodo(costi: list[tuple[date, Decimal]], dal: date, al: date) -> Decimal:
    """
    Costo istruttore di uno sport fra due date. `costi` sono le variazioni
    (valido dal mese, costo mensile): ogni mese usa l'ultima variazione già in vigore.
    """
    ordinati = sorted(costi)
    totale = Decimal("0.00")
    for m in mesi(dal, al):
        in_vigore = [c for valido, c in ordinati if valido <= m]
        if in_vigore:
            totale += in_vigore[-1]
    return totale


def normalizza_nome(nome: str) -> str:
    """Per riconoscere la stessa persona: minuscole, senza accenti né spazi doppi."""
    senza_accenti = "".join(
        ch for ch in unicodedata.normalize("NFKD", nome) if not unicodedata.combining(ch)
    )
    return " ".join(senza_accenti.lower().split())


def stesso_nome(a: str, b: str) -> bool:
    """Stesse parole, in qualsiasi ordine ("Rossi Mario" = "mario rossi")."""
    return sorted(normalizza_nome(a).split()) == sorted(normalizza_nome(b).split())
