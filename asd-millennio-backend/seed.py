"""
Seed database locale ASD Millennio.
Esegui dentro il container: docker compose exec backend python seed.py

Crea:
  - 4 soci (test-socio, test-staff, test-dirigenza + 1 minore)
  - Tessere attive per ogni socio/sport
  - Consensi GDPR
  - Pricing rules (tariffe base + leve + sconto promo demo)
  - Slot calendario 2027-01-01 → 2027-12-31 (solo Lun-Ven, 3 fasce/giorno)
  - 2 acquisti NFT demo (stato mintato) per test-socio
  - Wallet custodiale per test-socio
"""
import asyncio
import subprocess
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, "/app/src")

# ── Alembic migrate ────────────────────────────────────────────────────────────
print("▶ Esecuzione migrazioni Alembic…")
result = subprocess.run(
    ["alembic", "-c", "/app/alembic.ini", "upgrade", "head"],
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print("ERRORE alembic:", result.stderr)
    sys.exit(1)
print("✓ Migrazioni applicate\n")

# ── Import modelli ─────────────────────────────────────────────────────────────
from core.database import AsyncSessionLocal
from models.socio import Socio
from models.tessera import Tessera
from models.consenso import Consenso
from models.pricing_rule import PricingRule
from models.slot_calendario import SlotCalendario
from models.acquisto_nft import AcquistoNFT, AcquistoNFTSlot
from models.wallet import WalletCustodiale

# ── IDs Keycloak (da docker inspect dei container) ────────────────────────────
KC_SOCIO      = "071d8238-46f0-4269-ab8f-2ab73c4db749"
KC_STAFF      = "c946d3a1-0f46-4d13-a936-b00f6541e7c7"
KC_DIRIGENZA  = "1e31c633-251f-4a77-9c4e-82e5d8c80d2b"

ANNO_SPORTIVO = "2026-2027"
SCADENZA      = date(2027, 6, 30)
EMISSIONE     = date(2026, 9, 1)
NOW           = datetime.now(timezone.utc)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # ── Pulizia (idempotente) ──────────────────────────────────────────────
        print("▶ Pulizia tabelle esistenti…")
        for tbl in [
            "accesso_log", "acquisto_nft_slots", "acquisti_nft",
            "wallet_custodiali", "consensi", "tessere",
            "slot_calendario", "pricing_rules", "soci",
        ]:
            await db.execute(text(f"TRUNCATE TABLE {tbl} CASCADE"))
        await db.commit()
        print("✓ Tabelle svuotate\n")

        # ── 1. SOCI ────────────────────────────────────────────────────────────
        print("▶ Creazione soci…")

        id_socio     = uuid.uuid4()
        id_staff     = uuid.uuid4()
        id_dirigenza = uuid.uuid4()
        id_minore    = uuid.uuid4()

        soci = [
            Socio(
                id=id_socio,
                nome="Mario", cognome="Rossi",
                data_nascita=date(1990, 5, 15),
                codice_fiscale="RSSMRA90E15H501Z",
                email="test-socio@millennioasd.com",
                telefono="+39 333 1234567",
                indirizzo="Via Roma 1, Milano",
                sport=["volley"],
                keycloak_user_id=KC_SOCIO,
            ),
            Socio(
                id=id_staff,
                nome="Lucia", cognome="Bianchi",
                data_nascita=date(1985, 3, 22),
                codice_fiscale="BNCLCU85C62H501X",
                email="test-staff@millennioasd.com",
                telefono="+39 347 9876543",
                indirizzo="Via Garibaldi 10, Roma",
                sport=["badminton", "volley"],
                keycloak_user_id=KC_STAFF,
            ),
            Socio(
                id=id_dirigenza,
                nome="Carlo", cognome="Verdi",
                data_nascita=date(1978, 11, 8),
                codice_fiscale="VRDCRL78S08H501W",
                email="test-dirigenza@millennioasd.com",
                telefono="+39 328 5556677",
                indirizzo="Corso Italia 45, Torino",
                sport=["volley", "badminton", "kung_fu", "pickleball"],
                keycloak_user_id=KC_DIRIGENZA,
            ),
            Socio(
                id=id_minore,
                nome="Sofia", cognome="Rossi",
                data_nascita=date(2012, 7, 20),
                codice_fiscale="RSSSFO12L60H501V",
                email="sofia.rossi.minore@millennioasd.com",
                sport=["volley"],
                is_minor=True,
                tutore_id=id_socio,
                keycloak_user_id=None,
            ),
        ]
        for s in soci:
            db.add(s)
        await db.flush()
        print(f"  ✓ {len(soci)} soci creati")

        # ── 2. CONSENSI GDPR ──────────────────────────────────────────────────
        print("▶ Creazione consensi GDPR…")
        consensi = []
        for socio_id in [id_socio, id_staff, id_dirigenza]:
            for tipo in ["privacy", "trattamento_dati"]:
                consensi.append(Consenso(
                    id=uuid.uuid4(),
                    socio_id=socio_id,
                    tipo=tipo,
                    testo_versione="v1.0",
                    firmato_da=socio_id,
                    timestamp_firma=NOW,
                ))
        # Minore: consensi firmati dal tutore
        for tipo in ["privacy", "trattamento_dati", "foto_video"]:
            consensi.append(Consenso(
                id=uuid.uuid4(),
                socio_id=id_minore,
                tipo=tipo,
                testo_versione="v1.0",
                firmato_da=id_socio,
                timestamp_firma=NOW,
            ))
        for c in consensi:
            db.add(c)
        await db.flush()
        print(f"  ✓ {len(consensi)} consensi creati")

        # ── 3. TESSERE ────────────────────────────────────────────────────────
        print("▶ Creazione tessere…")
        tessere_data = [
            (id_socio,     "VOL-2026-00001", "volley"),
            (id_staff,     "BDM-2026-00001", "badminton"),
            (id_staff,     "VOL-2026-00002", "volley"),
            (id_dirigenza, "VOL-2026-00003", "volley"),
            (id_dirigenza, "BDM-2026-00002", "badminton"),
            (id_dirigenza, "KFU-2026-00001", "kung_fu"),
            (id_dirigenza, "PCK-2026-00001", "pickleball"),
            (id_minore,    "VOL-2026-00004", "volley"),
        ]
        tessere_objs = []
        for socio_id, numero, sport in tessere_data:
            t = Tessera(
                id=uuid.uuid4(),
                socio_id=socio_id,
                numero_tessera=numero,
                sport=sport,
                stato="attiva",
                data_emissione=EMISSIONE,
                data_scadenza=SCADENZA,
                anno_sportivo=ANNO_SPORTIVO,
            )
            db.add(t)
            tessere_objs.append(t)
        await db.flush()
        print(f"  ✓ {len(tessere_data)} tessere create (tutte attive)")

        # ── 4. WALLET CUSTODIALE per test-socio ──────────────────────────────
        print("▶ Creazione wallet custodiale demo…")
        wallet = WalletCustodiale(
            id=uuid.uuid4(),
            socio_id=id_socio,
            wallet_address="0x0b1374F8519a4Aa837B5100cF8cB520656b087a4",
            encrypted_private_key="DEMO_SEED_PLACEHOLDER_NOT_REAL",
        )
        db.add(wallet)
        await db.flush()
        print("  ✓ Wallet creato")

        # ── 5. PRICING RULES ──────────────────────────────────────────────────
        print("▶ Creazione pricing rules…")
        pricing = []

        # Tariffe base per fascia
        for fascia, tariffa in [("notte", 15), ("mattina", 20), ("pomeriggio", 25)]:
            pricing.append(PricingRule(
                id=uuid.uuid4(), tipo="tariffa_base", fascia=fascia,
                valore=tariffa, attivo=True,
                nome=f"Tariffa base {fascia} €{tariffa}/h",
            ))

        # Leva data (moltiplicatori per prossimità)
        for nome, smin, smax, val in [
            ("Leva data: >60gg",   61,  9999, 1.00),
            ("Leva data: 30-60gg", 30,  60,   1.10),
            ("Leva data: 15-30gg", 15,  30,   1.20),
            ("Leva data: 7-15gg",   7,  15,   1.35),
            ("Leva data: <7gg",     0,   7,   1.50),
        ]:
            pricing.append(PricingRule(
                id=uuid.uuid4(), tipo="leva_data", fascia=None,
                soglia_min=smin, soglia_max=smax,
                valore=val, attivo=True, nome=nome,
            ))

        # Leva scarsità (% ore libere)
        for nome, smin, smax, val in [
            ("Scarsità: >75% libere", 75, 100, 1.00),
            ("Scarsità: 50-75% libere", 50, 75, 1.10),
            ("Scarsità: 25-50% libere", 25, 50, 1.25),
            ("Scarsità: <25% libere",    0, 25, 1.40),
        ]:
            pricing.append(PricingRule(
                id=uuid.uuid4(), tipo="leva_scarsita", fascia=None,
                soglia_min=smin, soglia_max=smax,
                valore=val, attivo=True, nome=nome,
            ))

        # Sconto promo demo (10% su mattina, valido fino a fine anno)
        pricing.append(PricingRule(
            id=uuid.uuid4(), tipo="sconto_promo", fascia="mattina",
            valore=10, attivo=True,
            nome="Promo lancio — mattina -10%",
            valido_fino_a="2027-12-31",
            note="Sconto di lancio per il primo anno di vendite Palasirion",
        ))

        for p in pricing:
            db.add(p)
        await db.flush()
        print(f"  ✓ {len(pricing)} pricing rules create")

        # ── 6. SLOT CALENDARIO 2027 ────────────────────────────────────────────
        print("▶ Generazione slot calendario 2027 (Lun-Ven, 3 fasce)…")
        fasce_config = [
            ("notte",      time(0, 0),  time(7, 59),  8),
            ("mattina",    time(8, 0),  time(12, 59), 5),
            ("pomeriggio", time(13, 0), time(14, 59), 2),
        ]

        slot_count = 0
        giorno = date(2027, 1, 1)
        fine   = date(2027, 12, 31)
        slot_objs = []  # teniamo i primi slot per creare acquisti demo

        while giorno <= fine:
            if giorno.weekday() < 5:  # Lun=0 … Ven=4
                for fascia, ora_inizio, ora_fine, ore_tot in fasce_config:
                    s = SlotCalendario(
                        id=uuid.uuid4(),
                        data=giorno,
                        fascia=fascia,
                        ora_inizio=ora_inizio,
                        ora_fine=ora_fine,
                        ore_totali=ore_tot,
                        ore_vendute=[],
                        ore_in_lock=[],
                        stato="libero",
                    )
                    db.add(s)
                    slot_objs.append(s)
                    slot_count += 1
            giorno += timedelta(days=1)

        await db.flush()
        print(f"  ✓ {slot_count} slot generati (2027-01-01 → 2027-12-31)")

        # ── 7. ACQUISTI NFT DEMO ───────────────────────────────────────────────
        # Acquisto 1: 2 ore di notte (lunedì 6 gennaio 2027, ore 0 e 1) — mintato
        # Acquisto 2: 5 ore di mattina intera (lunedì 13 gennaio 2027) — mintato
        print("▶ Creazione acquisti NFT demo…")

        # Trova gli slot per 2027-01-06 notte e 2027-01-13 mattina
        slot_notte_6gen   = next((s for s in slot_objs if s.data == date(2027, 1, 6) and s.fascia == "notte"), None)
        slot_mattina_13gen = next((s for s in slot_objs if s.data == date(2027, 1, 13) and s.fascia == "mattina"), None)

        acq1_id = uuid.uuid4()
        acq2_id = uuid.uuid4()

        if slot_notte_6gen and slot_mattina_13gen:
            # Segna le ore come vendute
            slot_notte_6gen.ore_vendute = [0, 1]
            slot_notte_6gen.stato = "parziale"
            slot_notte_6gen.nft_token_id = 0

            slot_mattina_13gen.ore_vendute = [8, 9, 10, 11, 12]
            slot_mattina_13gen.stato = "esaurito"
            slot_mattina_13gen.nft_token_id = 1

            acq1 = AcquistoNFT(
                id=acq1_id,
                socio_id=id_socio,
                stripe_session_id="cs_test_seed_demo_001",
                stripe_payment_id="pi_test_seed_demo_001",
                token_id=0,
                contract_address="0xd96927D5981059931362Cb8c41aF0EBb539E633e",
                ipfs_uri="ipfs://QmSeedDemo001",
                ical_sha256="abc123seedhash001",
                importo_eur=30.00,
                stato="mintato",
                wallet_address="0x0b1374F8519a4Aa837B5100cF8cB520656b087a4",
            )
            acq2 = AcquistoNFT(
                id=acq2_id,
                socio_id=id_socio,
                stripe_session_id="cs_test_seed_demo_002",
                stripe_payment_id="pi_test_seed_demo_002",
                token_id=1,
                contract_address="0xd96927D5981059931362Cb8c41aF0EBb539E633e",
                ipfs_uri="ipfs://QmSeedDemo002",
                ical_sha256="abc123seedhash002",
                importo_eur=90.00,
                stato="mintato",
                wallet_address="0x0b1374F8519a4Aa837B5100cF8cB520656b087a4",
            )
            db.add(acq1)
            db.add(acq2)
            await db.flush()

            link1 = AcquistoNFTSlot(
                acquisto_nft_id=acq1_id,
                slot_calendario_id=slot_notte_6gen.id,
                ore_acquistate=[0, 1],
            )
            link2 = AcquistoNFTSlot(
                acquisto_nft_id=acq2_id,
                slot_calendario_id=slot_mattina_13gen.id,
                ore_acquistate=[8, 9, 10, 11, 12],
            )
            db.add(link1)
            db.add(link2)
            await db.flush()
            print("  ✓ 2 acquisti NFT demo creati (token #0 e #1)")
        else:
            print("  ⚠ Slot per acquisti demo non trovati — skip")

        await db.commit()

    print("\n" + "=" * 60)
    print("SEED COMPLETATO")
    print("=" * 60)
    print("\nAccount disponibili:")
    print("  test-socio     / Benito12.  → socio con tessera volley attiva + 2 NFT")
    print("  test-staff     / Benito12.  → staff con tessere badminton+volley")
    print("  test-dirigenza / Benito12.  → dirigenza con 4 sport")
    print("\nDashboard:")
    print("  Frontend:  http://localhost:3000")
    print("  API docs:  http://localhost:8000/docs")
    print("  Keycloak:  http://localhost:8080/admin  (admin / admin)")


if __name__ == "__main__":
    asyncio.run(main())
