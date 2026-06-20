"""
Motore di pricing dinamico per gli slot Palasirion.

Formula: prezzo_ora = tariffa_base × leva_data × leva_scarsita × (1 - sconto_promo / 100)

Le regole sono lette dal DB (tabella pricing_rules), gestite dalla dashboard dirigenza.
Il pricing è sempre calcolato server-side — il frontend riceve solo il prezzo finale.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from models.pricing_rule import PricingRule
from models.slot_calendario import SlotCalendario

FASCE = ("notte", "mattina", "pomeriggio")

# Tariffe fallback se la DB non ha ancora regole
_TARIFFE_FALLBACK: dict[str, Decimal] = {
    "notte": Decimal("15.00"),
    "mattina": Decimal("20.00"),
    "pomeriggio": Decimal("25.00"),
}


class _CachedRules:
    """Regole di pricing caricate una volta sola per sessione di calcolo."""

    def __init__(self, rules: list) -> None:
        self.tariffe: dict[str, Decimal] = dict(_TARIFFE_FALLBACK)
        self.leva_data: list = []
        self.leva_scarsita: list = []
        self.sconti_promo: list = []

        for r in rules:
            if r.tipo == "tariffa_base" and r.fascia:
                self.tariffe[r.fascia] = Decimal(str(r.valore))
            elif r.tipo == "leva_data":
                self.leva_data.append(r)
            elif r.tipo == "leva_scarsita":
                self.leva_scarsita.append(r)
            elif r.tipo == "sconto_promo":
                self.sconti_promo.append(r)

        self.leva_data.sort(key=lambda r: float(r.soglia_min or 0), reverse=True)
        self.leva_scarsita.sort(key=lambda r: float(r.soglia_min or 0), reverse=True)

    def get_tariffa(self, fascia: str) -> Decimal:
        return self.tariffe.get(fascia, _TARIFFE_FALLBACK.get(fascia, Decimal("0")))

    def get_mol_data(self, giorni_mancanti: int) -> Decimal:
        for r in self.leva_data:
            s_min = float(r.soglia_min) if r.soglia_min is not None else None
            s_max = float(r.soglia_max) if r.soglia_max is not None else None
            if s_min is None and s_max is not None:
                if giorni_mancanti < s_max:
                    return Decimal(str(r.valore))
            elif s_min is not None and s_max is None:
                if giorni_mancanti >= s_min:
                    return Decimal(str(r.valore))
            elif s_min is not None and s_max is not None:
                if s_min <= giorni_mancanti < s_max:
                    return Decimal(str(r.valore))
        return Decimal("1.00")

    def get_mol_scarsita(self, pct_libere: float) -> Decimal:
        for r in self.leva_scarsita:
            s_min = float(r.soglia_min) if r.soglia_min is not None else None
            s_max = float(r.soglia_max) if r.soglia_max is not None else None
            if s_min is None and s_max is not None:
                if pct_libere < s_max:
                    return Decimal(str(r.valore))
            elif s_min is not None and s_max is None:
                if pct_libere >= s_min:
                    return Decimal(str(r.valore))
            elif s_min is not None and s_max is not None:
                if s_min <= pct_libere < s_max:
                    return Decimal(str(r.valore))
        return Decimal("1.00")

    def get_sconto(self, fascia: str, data_slot: date) -> Decimal:
        oggi = date.today()
        applicabili = [
            float(r.valore)
            for r in self.sconti_promo
            if (r.fascia is None or r.fascia == fascia)
            and (r.valido_fino_a is None or date.fromisoformat(r.valido_fino_a) >= oggi)
        ]
        return Decimal(str(max(applicabili))) if applicabili else Decimal("0")


class PricingEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _load_rules(self) -> _CachedRules:
        """Carica tutte le regole attive in un'unica query."""
        result = await self.db.execute(
            select(PricingRule).where(PricingRule.attivo.is_(True))
        )
        return _CachedRules(list(result.scalars().all()))

    async def _get_pct_libere_per_fascia(self, fasce: set[str]) -> dict[str, float]:
        """Calcola % ore libere per ogni fascia richiesta in due query."""
        totali: dict[str, int] = {}
        vendute_count: dict[str, int] = {}
        for fascia in fasce:
            res = await self.db.execute(
                select(func.sum(SlotCalendario.ore_totali)).where(
                    SlotCalendario.fascia == fascia
                )
            )
            totali[fascia] = int(res.scalar() or 0)

            res2 = await self.db.execute(
                select(SlotCalendario.ore_vendute).where(SlotCalendario.fascia == fascia)
            )
            vendute_count[fascia] = sum(len(row or []) for (row,) in res2)

        result: dict[str, float] = {}
        for fascia in fasce:
            tot = totali.get(fascia, 0)
            if tot == 0:
                result[fascia] = 100.0
            else:
                vend = vendute_count.get(fascia, 0)
                result[fascia] = ((tot - vend) / tot) * 100
        return result

    def _calcola_prezzo_ora(
        self,
        fascia: str,
        data_slot: date,
        rules: _CachedRules,
        pct_libere_fascia: float,
    ) -> dict:
        giorni_mancanti = max(0, (data_slot - date.today()).days)
        tariffa_base = rules.get_tariffa(fascia)
        mol_data = rules.get_mol_data(giorni_mancanti)
        mol_scarsita = rules.get_mol_scarsita(pct_libere_fascia)
        sconto_pct = rules.get_sconto(fascia, data_slot)
        prezzo = (tariffa_base * mol_data * mol_scarsita * (1 - sconto_pct / 100)).quantize(
            Decimal("0.01")
        )
        return {
            "fascia": fascia,
            "data": data_slot.isoformat(),
            "tariffa_base": float(tariffa_base),
            "moltiplicatore_data": float(mol_data),
            "moltiplicatore_scarsita": float(mol_scarsita),
            "sconto_promo_pct": float(sconto_pct),
            "prezzo_ora": float(prezzo),
        }

    async def calcola_prezzo_ora(self, fascia: str, data_slot: date) -> dict:
        """Prezzo per singola ora — usato per preview singola fascia."""
        rules = await self._load_rules()
        pct_map = await self._get_pct_libere_per_fascia({fascia})
        return self._calcola_prezzo_ora(fascia, data_slot, rules, pct_map[fascia])

    async def calcola_prezzo_selezione(self, selezione: list[dict]) -> dict:
        """
        Calcola il prezzo totale per una selezione di ore.
        Una sola batch di query DB indipendentemente da quanti slot.

        selezione: [{"slot": SlotCalendario, "ore": [8, 9, 10]}, ...]
        """
        if not selezione:
            return {"ore_notte": 0, "ore_mattina": 0, "ore_pomeriggio": 0,
                    "costo_totale": 0.0, "dettaglio": []}

        # Carica tutto in anticipo — 1 query rules + 2 query per fascia unica
        rules = await self._load_rules()
        fasce_usate = {item["slot"].fascia for item in selezione if item.get("ore")}
        pct_map = await self._get_pct_libere_per_fascia(fasce_usate)

        costo_totale = Decimal("0")
        dettaglio: list[dict] = []

        for item in selezione:
            slot: SlotCalendario = item["slot"]
            ore: list[int] = item["ore"]
            if not ore:
                continue

            pct_libere = pct_map.get(slot.fascia, 100.0)
            info = self._calcola_prezzo_ora(slot.fascia, slot.data, rules, pct_libere)
            costo_slot = Decimal(str(info["prezzo_ora"])) * len(ore)
            costo_totale += costo_slot

            dettaglio.append({
                **info,
                "slot_id": str(slot.id),
                "ore_selezionate": ore,
                "n_ore": len(ore),
                "costo_slot": float(costo_slot),
            })

        ore_per_fascia: dict[str, int] = {"notte": 0, "mattina": 0, "pomeriggio": 0}
        for d in dettaglio:
            ore_per_fascia[d["fascia"]] += d["n_ore"]

        return {
            "ore_notte": ore_per_fascia["notte"],
            "ore_mattina": ore_per_fascia["mattina"],
            "ore_pomeriggio": ore_per_fascia["pomeriggio"],
            "costo_totale": float(costo_totale.quantize(Decimal("0.01"))),
            "dettaglio": dettaglio,
        }
