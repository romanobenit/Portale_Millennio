"""
Seed delle pricing rules di default per l'anno sportivo 2026-2027.

Inserisce:
  - Tariffe base per fascia (notte €15/h, mattina €20/h, pomeriggio €25/h)
  - Leva data (5 fasce: >60g, 30-60g, 15-30g, 7-15g, <7g)
  - Leva scarsità (4 fasce: >75%, 50-75%, 25-50%, <25%)

Idempotente: non inserisce se esistono già regole dello stesso tipo+nome.

Uso:
  cd asd-millennio-backend
  python src/scripts/seed_pricing_rules.py [--dry-run]
"""
import asyncio
import sys
import uuid

from sqlalchemy import select

sys.path.insert(0, "src")

from core.database import AsyncSessionLocal  # noqa: E402
from models.pricing_rule import PricingRule  # noqa: E402

REGOLE_DEFAULT: list[dict] = [
    # ── Tariffe base ─────────────────────────────────────────────────────────
    {"tipo": "tariffa_base", "fascia": "notte",      "valore": 15.0,  "nome": "Tariffa base Notte (€/h)"},
    {"tipo": "tariffa_base", "fascia": "mattina",    "valore": 20.0,  "nome": "Tariffa base Mattina (€/h)"},
    {"tipo": "tariffa_base", "fascia": "pomeriggio", "valore": 25.0,  "nome": "Tariffa base Pomeriggio (€/h)"},

    # ── Leva 1: Prossimità alla data ─────────────────────────────────────────
    # soglia_min/max = giorni mancanti, valore = moltiplicatore
    {"tipo": "leva_data", "fascia": None, "soglia_min": 60,   "soglia_max": None,  "valore": 1.00, "nome": "Leva data >60 giorni (×1.00)"},
    {"tipo": "leva_data", "fascia": None, "soglia_min": 30,   "soglia_max": 60,    "valore": 1.10, "nome": "Leva data 30-60 giorni (×1.10)"},
    {"tipo": "leva_data", "fascia": None, "soglia_min": 15,   "soglia_max": 30,    "valore": 1.20, "nome": "Leva data 15-30 giorni (×1.20)"},
    {"tipo": "leva_data", "fascia": None, "soglia_min": 7,    "soglia_max": 15,    "valore": 1.35, "nome": "Leva data 7-15 giorni (×1.35)"},
    {"tipo": "leva_data", "fascia": None, "soglia_min": None, "soglia_max": 7,     "valore": 1.50, "nome": "Leva data <7 giorni (×1.50)"},

    # ── Leva 2: Scarsità ore disponibili ─────────────────────────────────────
    # soglia_min/max = % ore ancora libere nella fascia (0–100)
    {"tipo": "leva_scarsita", "fascia": None, "soglia_min": 75,   "soglia_max": None, "valore": 1.00, "nome": "Scarsità >75% libere (×1.00)"},
    {"tipo": "leva_scarsita", "fascia": None, "soglia_min": 50,   "soglia_max": 75,   "valore": 1.10, "nome": "Scarsità 50-75% libere (×1.10)"},
    {"tipo": "leva_scarsita", "fascia": None, "soglia_min": 25,   "soglia_max": 50,   "valore": 1.25, "nome": "Scarsità 25-50% libere (×1.25)"},
    {"tipo": "leva_scarsita", "fascia": None, "soglia_min": None, "soglia_max": 25,   "valore": 1.40, "nome": "Scarsità <25% libere (×1.40)"},
]


async def _seed(dry_run: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        esistenti_result = await db.execute(select(PricingRule.nome))
        esistenti_nomi: set[str] = {r.nome for r in esistenti_result}

        da_inserire: list[PricingRule] = []
        for r in REGOLE_DEFAULT:
            if r["nome"] in esistenti_nomi:
                print(f"  SKIP (già presente): {r['nome']}")
                continue
            da_inserire.append(PricingRule(id=uuid.uuid4(), **r))

        print(f"\nPricing rules da inserire: {len(da_inserire)}")

        if dry_run:
            for r in da_inserire:
                print(f"  [DRY-RUN] {r.nome}")
            return

        if da_inserire:
            db.add_all(da_inserire)
            await db.commit()
            print(f"  OK: {len(da_inserire)} regole inserite.")
        else:
            print("  Nessuna nuova regola da inserire.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    asyncio.run(_seed(dry_run=dry))
