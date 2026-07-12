 # ASD Millennio — Piattaforma Digitale MVP

> Piattaforma integrata per la gestione di soci, tessere, calendario Palasirio e raccolta fondi via NFT ERC-721 su Polygon.
> Sviluppata per **ASD Millennio** (volley · badminton · kung fu · pickleball) — impianto Palasirio, regime ATI.

---

## Indice

1. [Panoramica architetturale](#1-panoramica-architetturale)
2. [Stack tecnologico](#2-stack-tecnologico)
3. [Struttura repository](#3-struttura-repository)
4. [Prerequisiti](#4-prerequisiti)
5. [Setup locale](#5-setup-locale)
   - [5.1 Variabili d'ambiente](#51-variabili-dambiente)
   - [5.2 Avvio con Docker Compose](#52-avvio-con-docker-compose)
   - [5.3 Avvio manuale (sviluppo)](#53-avvio-manuale-sviluppo)
   - [5.4 Configurazione Keycloak](#54-configurazione-keycloak)
   - [5.5 Seed database](#55-seed-database)
6. [API Reference](#6-api-reference)
7. [Smart contract](#7-smart-contract)
8. [Test](#8-test)
9. [CI/CD](#9-cicd)
10. [Deploy in produzione](#10-deploy-in-produzione)
11. [Infrastruttura Hetzner](#11-infrastruttura-hetzner)
12. [Sicurezza e compliance](#12-sicurezza-e-compliance)
13. [Rotazione chiavi e segreti](#13-rotazione-chiavi-e-segreti)
14. [Troubleshooting](#14-troubleshooting)
15. [Decisioni architetturali](#15-decisioni-architetturali)
16. [Roadmap fuori scope MVP](#16-roadmap-fuori-scope-mvp)

---

## 1. Panoramica architetturale

```
┌─────────────────────────────────────────────────────────────────┐
│                        Cliente (browser)                        │
│              Next.js 14 SSR — millennioasd.com                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / TLS 1.3
                ┌───────────▼────────────┐
                │   Hetzner Load Balancer │  LB11 — HTTPS termination
                │   + Hetzner Firewall    │  solo 443/80 pubblici
                └──────┬──────────┬───────┘
                       │          │
          ┌────────────▼──┐  ┌────▼───────────────┐
          │  Backend API  │  │   Frontend Next.js  │
          │  FastAPI :8000│  │   :3000             │
          │  4 workers    │  │                     │
          └──────┬────────┘  └────────────────────-┘
                 │
     ┌───────────┼────────────┬──────────────────┐
     │           │            │                  │
┌────▼───┐ ┌────▼────┐ ┌─────▼──────┐ ┌────────▼───────┐
│Postgres│ │  Redis  │ │  Keycloak  │ │ Celery Worker  │
│  :5432 │ │  :6379  │ │  :8080     │ │ (mint NFT async)│
│ vol 40G│ │ persist │ │            │ │                │
└────────┘ └─────────┘ └────────────┘ └────────┬───────┘
                                                │
                                    ┌───────────▼──────────┐
                                    │  Polygon (Amoy/PoS)  │
                                    │  PalasirioNFT.sol   │
                                    │  + Pinata IPFS       │
                                    └──────────────────────┘
```

### Flusso acquisto NFT (critico — max 60 secondi end-to-end)

```
Socio seleziona slot → GET /api/v1/calendario/riepilogo-selezione (prezzo server-side)
  → POST /api/v1/nft/acquisto (lock slot 30min + crea Stripe Session)
  → Stripe Checkout (hosted page — ASD mai vede dati carta)
  → POST /api/v1/webhooks/stripe (checkout.session.completed)
  → webhook verifica firma + idempotency check
  → esegui_mint_task.delay() [Celery async]
    → genera iCal RFC 5545
    → backup metadati off-chain (DB)
    → upload JSON metadati → Pinata IPFS
    → mint ERC-721 on-chain (Polygon)
    → slot → nft_venduto, acquisto → mintato
    → email socio (Resend): iCal + Token ID + Polygonscan link
```

---

## 2. Stack tecnologico

| Layer | Tecnologia | Versione | Note |
|---|---|---|---|
| Backend | FastAPI + uvicorn | ≥ 0.111 / ≥ 0.29 | Async, 4 workers prod |
| ORM | SQLAlchemy async | ≥ 2.0 | `asyncpg` driver |
| Database | PostgreSQL | 16 | Volume persistente Hetzner |
| Cache / broker | Redis | 7 | AOF persistence, broker Celery |
| Task queue | Celery | ≥ 5.3 | `task_acks_late=True` — no lost mints |
| Auth | Keycloak | 24 | SSO, MFA, JWKS via PyJWT |
| JWT validation | PyJWT | ≥ 2.8 | RS256, PyJWKClient con cache 300s |
| Rate limiting | slowapi | ≥ 0.1.9 | Fixed-window, storage Redis |
| Blockchain | Polygon PoS | — | Testnet: Amoy (80002), Mainnet: 137 |
| Smart contract | Solidity + OpenZeppelin | 0.8.24 / v5 | Soulbound-like ERC-721 |
| IPFS | Pinata | — | Metadati NFT + iCal base64 |
| Pagamenti | Stripe Checkout | SDK ≥ 9.0 | Hosted page, webhook idempotency |
| Wallet custodiale | eth-account + cryptography | — | AES-256-GCM, chiavi mai in chiaro |
| PDF tessera | reportlab + qrcode[pil] | ≥ 4.1 / ≥ 7.4 | On-the-fly, nessun file su disco |
| Email | Resend | — | Transazionali (mint, scadenze) |
| Frontend | Next.js 14 | App Router, SSR | |
| Styling | Tailwind CSS | ≥ 3.4 | |
| Linting/fmt | ruff + black (BE), ESLint + tsc (FE) | | |
| CI/CD | GitHub Actions | — | Test → build → deploy SSH |
| Cloud | Hetzner Cloud | — | FSN1/NBG1, rete privata, GDPR UE |
| Container | Docker Compose | v3.9 | Zero-downtime per-service |

---

## 3. Struttura repository

```
flussocrazia/                          ← root del monorepo locale
├── docker-compose.yml                 ← orchestrazione locale completa
├── .env                               ← NON committare — creato da .env.example
├── README.md                          ← questo file
│
├── asd-millennio-backend/
│   ├── Dockerfile
│   ├── requirements.txt               ← dipendenze produzione
│   ├── requirements-dev.txt           ← + pytest, black, ruff, faker
│   ├── pytest.ini                     ← asyncio_mode=auto, pythonpath=src
│   ├── alembic.ini                    ← migrations via DATABASE_URL env var
│   ├── .env.example                   ← template variabili d'ambiente
│   ├── .github/workflows/ci.yml       ← lint → test (cov ≥ 80%) → build Docker
│   └── src/
│       ├── main.py                    ← FastAPI app, routers, CORS, rate limit
│       ├── core/
│       │   ├── config.py              ← Settings Pydantic (lru_cache)
│       │   ├── database.py            ← engine async, get_db, AsyncSessionLocal
│       │   ├── security.py            ← JWT decode, require_roles, guards
│       │   ├── rate_limit.py          ← slowapi Limiter (Redis, fixed-window)
│       │   ├── celery_app.py          ← Celery broker Redis, task_acks_late=True
│       │   ├── redis.py               ← client Redis async
│       │   └── logger.py              ← setup logging strutturato
│       ├── models/                    ← SQLAlchemy ORM (un file per entità)
│       │   ├── socio.py
│       │   ├── tessera.py
│       │   ├── acquisto_nft.py        ← AcquistoNFT, AcquistoNFTSlot, AccessoLog
│       │   ├── consenso.py
│       │   ├── slot_calendario.py
│       │   ├── wallet.py              ← WalletCustodiale (chiave cifrata AES-256)
│       │   └── webhook_log.py         ← idempotency Stripe webhooks
│       ├── schemas/                   ← Pydantic v2 (Request/Response separati)
│       │   ├── soci.py
│       │   ├── tessere.py
│       │   ├── calendario.py
│       │   ├── nft.py
│       │   └── consensi.py
│       ├── modules/
│       │   ├── soci/
│       │   │   ├── router.py          ← M01: CRUD soci, tessere, consensi
│       │   │   ├── tessere_router.py  ← endpoint pubblici verifica QR + PDF
│       │   │   ├── service.py         ← business logic, GDPR erasure (Art. 17)
│       │   │   ├── repository.py      ← query DB
│       │   │   └── pdf.py             ← genera PDF tessera A5 on-the-fly
│       │   ├── calendario/
│       │   │   ├── router.py          ← M02: slot, riepilogo, ATI feed
│       │   │   └── service.py         ← lock ottimistico, calcolo prezzo
│       │   ├── nft/
│       │   │   ├── router.py          ← M04: acquisto, verifica QR, dashboard
│       │   │   ├── service.py         ← avvia_acquisto, conferma_pagamento
│       │   │   ├── ical.py            ← genera RFC 5545, calcola SHA-256
│       │   │   ├── ipfs.py            ← Pinata upload, costruisci_metadati_nft
│       │   │   ├── blockchain.py      ← web3.py, mint_nft on-chain
│       │   │   └── wallet.py          ← genera_wallet, cifra/decifra AES-256-GCM
│       │   └── webhooks/
│       │       └── stripe_handler.py  ← firma, idempotency, checkout.session.completed
│       ├── tasks/
│       │   └── mint.py                ← Celery task: iCal→IPFS→mint (retry 3×, backoff)
│       ├── scripts/
│       │   └── seed_slot_calendario.py ← 130 giorni ATI × 16 slot = 2.080 slot
│       ├── migrations/
│       │   ├── env.py
│       │   └── versions/
│       │       ├── 20260601_120000_create_soci.py
│       │       └── 20260601_130000_create_calendario_nft.py
│       └── tests/
│           ├── conftest.py            ← fixtures DB, client, mock_jwt_user
│           ├── unit/
│           │   ├── test_soci_service.py      ← 12 test (GDPR, tessere, minori)
│           │   ├── test_calendario_service.py ← 8 test (tariffe, lock, prezzo)
│           │   ├── test_pdf.py               ← 3 test (bytes, magic %PDF, sport)
│           │   ├── test_seed.py              ← 4 test (130 giorni, 16 slot/day)
│           │   └── test_wallet.py            ← 2 test (AES-256 round-trip)
│           └── integration/                  ← (da completare con DB reale)
│
├── asd-millennio-frontend/
│   ├── Dockerfile
│   ├── package.json                   ← Next.js 14, keycloak-js, Stripe.js, zustand
│   ├── tsconfig.json
│   ├── .eslintrc.json
│   ├── .github/workflows/ci.yml       ← lint → tsc → next build
│   └── app/
│       ├── (auth)/                    ← pagine autenticazione Keycloak
│       ├── dashboard/                 ← area soci autenticati
│       ├── staff/                     ← verifica QR Palasirio
│       └── dirigenza/                 ← dashboard fundraising
│
└── asd-millennio-contracts/
    ├── package.json                   ← Hardhat, OpenZeppelin v5
    ├── hardhat.config.js              ← networks: amoy, polygon
    ├── .github/workflows/ci.yml       ← compile → test → coverage ≥ 95%
    ├── contracts/
    │   ├── PalasirioNFT.sol          ← ERC-721 + soulbound + escrow mint
    │   └── interfaces/
    │       └── IPalasirioNFT.sol
    ├── scripts/
    │   ├── deploy.js
    │   └── verify.js
    └── test/
        └── PalasirioNFT.test.js
```

---

## 4. Prerequisiti

### Software richiesto

| Tool | Versione minima | Verifica |
|---|---|---|
| Python | 3.12 | `python --version` |
| Node.js | 20 LTS | `node --version` |
| npm | 10 | `npm --version` |
| Docker | 24 | `docker --version` |
| Docker Compose | v2 plugin | `docker compose version` |
| Git | 2.40 | `git --version` |

### Account e credenziali esterne (per funzionalità complete)

| Servizio | Uso | Dove ottenerlo |
|---|---|---|
| **Stripe** | Pagamenti Checkout | [dashboard.stripe.com](https://dashboard.stripe.com) |
| **Pinata** | Storage IPFS metadati NFT | [app.pinata.cloud](https://app.pinata.cloud) |
| **Alchemy / QuickNode** | RPC Polygon Amoy (testnet) | [alchemy.com](https://www.alchemy.com) |
| **Resend** | Email transazionali | [resend.com](https://resend.com) |
| **Hetzner Cloud** | Infrastruttura produzione | [hetzner.com/cloud](https://www.hetzner.com/cloud) |

> In sviluppo locale puoi avviare senza Stripe, Pinata e Polygon: l'API risponde, ma il flusso di acquisto NFT non sarà completo senza queste credenziali.

---

## 5. Setup locale

### 5.1 Variabili d'ambiente

```bash
# Dalla root del progetto
cp asd-millennio-backend/.env.example .env
```

Apri `.env` e compila i campi obbligatori:

```bash
# ─── Database ───────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/millennio

# ─── Redis ──────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ─── Keycloak ───────────────────────────────────────────────────
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=millennio-asd
KEYCLOAK_CLIENT_ID=millennio-backend
KEYCLOAK_CLIENT_SECRET=<generato dalla console Keycloak>

# ─── Stripe (test mode) ─────────────────────────────────────────
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...      # da: stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
STRIPE_PUBLISHABLE_KEY=pk_test_...

# ─── Blockchain — Polygon Amoy testnet ──────────────────────────
POLYGON_RPC_URL=https://polygon-amoy.g.alchemy.com/v2/<API_KEY>
POLYGON_CHAIN_ID=80002
CONTRACT_ADDRESS_PALASIRIO_NFT=0x...
MINTER_PRIVATE_KEY=<chiave privata wallet minter — MAI committare>

# ─── IPFS / Pinata ──────────────────────────────────────────────
PINATA_API_KEY=...
PINATA_SECRET_KEY=...
PINATA_GATEWAY_URL=https://gateway.pinata.cloud

# ─── Wallet custodiale ───────────────────────────────────────────
# AES-256 key: 32 byte = 64 caratteri esadecimali
WALLET_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# ─── Email ───────────────────────────────────────────────────────
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@millennioasd.com

# ─── App ─────────────────────────────────────────────────────────
NODE_ENV=development
APP_URL=http://localhost:3000
JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# ─── ATI feed ────────────────────────────────────────────────────
ATI_API_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ATI_API_KEY_EXPIRES_AT=2027-06-30

# ─── Business logic ──────────────────────────────────────────────
FUNDRAISING_TARGET_EUR=50000
ANNO_SPORTIVO_CORRENTE=2026-2027
TESSERA_SCADENZA_MESE=6
TESSERA_SCADENZA_GIORNO=30
```

> **Sicurezza:** Il file `.env` è in `.gitignore`. Non committarlo mai. Le chiavi generate con `secrets.token_hex(32)` sono crittograficamente sicure.

---

### 5.2 Avvio con Docker Compose

```bash
# Dalla root del progetto (dove si trova docker-compose.yml)
docker compose up -d

# Verifica che tutti i servizi siano healthy
docker compose ps

# Output atteso:
# NAME              STATUS          PORTS
# postgres          healthy         5432/tcp
# redis             healthy         6379/tcp
# keycloak          running         8080/tcp
# backend           running         8000/tcp
# celery-worker     healthy
# frontend          running         3000/tcp
```

**Primo avvio — applicare le migrazioni:**

```bash
docker compose exec backend alembic upgrade head
```

**Seed slot calendario (anno sportivo 2026-2027):**

```bash
docker compose exec backend python src/scripts/seed_slot_calendario.py
# Output: Anno sportivo 2026-2027: 130 giorni ATI × 16 slot/giorno = 2080 slot totali
```

**Verifica salute del backend:**

```bash
curl http://localhost:8000/health
# {"status":"ok","env":"development"}
```

**Documentazione interattiva API (solo in development):**

```
http://localhost:8000/docs      ← Swagger UI
http://localhost:8000/redoc     ← ReDoc
```

---

### 5.3 Avvio manuale (sviluppo senza Docker)

Questo setup è utile per debug rapido del backend con hot-reload.

**Requisiti:**
- PostgreSQL 16 in esecuzione su `localhost:5432` con database `millennio`
- Redis 7 in esecuzione su `localhost:6379`
- Keycloak 24 in esecuzione su `localhost:8080` (puoi avviare solo Keycloak via Docker)

```bash
# ─── Backend ────────────────────────────────────────────────────
cd asd-millennio-backend

# Crea e attiva virtualenv
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# oppure:
.venv\Scripts\Activate.ps1        # Windows PowerShell

# Installa dipendenze
pip install -r requirements-dev.txt

# Copia .env dal template (se non già fatto)
cp .env.example .env
# Edita .env con i valori locali

# Applica migrazioni
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/millennio \
  alembic upgrade head

# Avvia backend con hot-reload
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# In un secondo terminale: avvia worker Celery
cd asd-millennio-backend/src
celery -A core.celery_app.celery_app worker --loglevel=info --concurrency=2
```

```bash
# ─── Frontend ───────────────────────────────────────────────────
cd asd-millennio-frontend
npm install
npm run dev
# → http://localhost:3000
```

```bash
# ─── Avvia solo le infrastrutture via Docker (consigliato in sviluppo) ───
docker compose up -d postgres redis keycloak
```

---

### 5.4 Configurazione Keycloak

Accedi alla console di amministrazione Keycloak: `http://localhost:8080`
Credenziali default Docker Compose: `admin` / `admin`

#### Crea il Realm

1. Clicca **Create Realm**
2. Nome realm: **`millennio-asd`** (esatto — usato in tutti i JWT)
3. Salva

#### Crea il Client backend

1. **Clients** → **Create client**
2. Client ID: `millennio-backend`
3. Client authentication: **ON** (confidential)
4. Standard flow: **ON**, Direct access grants: **ON**
5. Salva → tab **Credentials** → copia **Client Secret** → incolla in `.env` come `KEYCLOAK_CLIENT_SECRET`

#### Crea il Client frontend

1. Client ID: `millennio-frontend`
2. Client authentication: **OFF** (public)
3. Valid redirect URIs: `http://localhost:3000/*`
4. Web origins: `http://localhost:3000`

#### Crea i Ruoli del Realm

**Realm roles** → **Create role** per ciascuno:

| Ruolo | Descrizione |
|---|---|
| `socio` | Accesso self-service (tessera, acquisto NFT) |
| `allenatore` | Presenze, calendario, comunicazioni |
| `staff` | Tesseramento, verifica QR Palasirio |
| `dirigenza` | Report, dashboard fundraising, approvazioni |

#### MFA obbligatorio per staff e dirigenza

1. **Authentication** → **Required actions** → abilita **Configure OTP**
2. **Flows** → per i ruoli `staff` e `dirigenza` aggiungi OTP come required

#### Crea un utente di test

1. **Users** → **Add user**
2. Username: `test-socio`, Email: `test@millennioasd.local`
3. **Credentials** → imposta password → disabilita "Temporary"
4. **Role mappings** → assegna `socio`

---

### 5.5 Seed database

```bash
# Slot calendario anno sportivo 2026-2027
# (Martedì, Giovedì, Sabato — 130 giorni × 16 slot orari = 2.080 slot)
docker compose exec backend python src/scripts/seed_slot_calendario.py

# Dry-run (mostra count senza scrivere)
docker compose exec backend python src/scripts/seed_slot_calendario.py --dry-run
```

**Struttura slot generati:**

| Fascia | Orari | Ore | Tariffa | Slot/giorno |
|---|---|---|---|---|
| Notte | 00:00 – 08:00 | 1h ciascuno | €15/h | 8 |
| Mattina | 08:00 – 13:00 | 1h ciascuno | €20/h | 5 |
| Pomeriggio | 13:00 – 16:00 | 1h ciascuno | €18/h | 3 |

---

## 6. API Reference

Tutti gli endpoint sono sotto il prefisso `/api/v1`.
La documentazione interattiva completa (Swagger UI) è disponibile su `/docs` in ambiente `development`.

### Autenticazione

Tutti gli endpoint protetti richiedono un JWT Keycloak nell'header:

```
Authorization: Bearer <access_token>
```

Il token viene validato con PyJWT RS256 contro il JWKS endpoint di Keycloak.
Il client JWKS usa caching interno (TTL 300s, max 16 chiavi) per prestazioni ottimali.

### M01 — Soci e Tessere

| Method | Path | Auth | Descrizione |
|---|---|---|---|
| `GET` | `/soci` | `staff` / `dirigenza` | Lista soci paginata (`?page=1&limit=20`) |
| `POST` | `/soci` | `staff` | Crea nuovo socio |
| `POST` | `/soci/import` | `staff` | Import massivo CSV (202 Accepted, async) |
| `GET` | `/soci/me` | qualsiasi ruolo | Profilo del socio corrente (link Keycloak auto) |
| `GET` | `/soci/{id}` | `staff` / owner | Dettaglio socio |
| `PATCH` | `/soci/{id}` | `staff` / owner | Aggiorna socio |
| `DELETE` | `/soci/{id}` | `dirigenza` / owner | GDPR Art. 17 — pseudoanonimizzazione |
| `GET` | `/soci/{id}/consensi` | `staff` / owner | Lista consensi GDPR |
| `POST` | `/soci/{id}/consensi` | `staff` / owner | Firma consenso |
| `DELETE` | `/soci/{id}/consensi/{tipo}` | `staff` / owner | Revoca consenso |
| `GET` | `/soci/{id}/minori` | `staff` / tutore | Lista minori del tutore |
| `GET` | `/soci/{id}/tessere` | `staff` / owner | Tessere del socio |
| `POST` | `/soci/{id}/tessere` | `staff` | Emette nuova tessera |
| `POST` | `/soci/{id}/tessere/{tid}/attiva` | `staff` | Attiva tessera → imposta `pdf_url` |
| `GET` | `/tessere/{id}/verifica` | **pubblico** | Verifica tessera via QR code |
| `GET` | `/tessere/{id}/pdf` | **pubblico** | Download PDF tessera A5 con QR |

**Formato numero tessera:** `{SPORT}-{ANNO_INIZIO}-{PROGRESSIVO_5_CIFRE}`
Esempi: `VOL-2026-00042`, `BDM-2026-00007`, `KFU-2026-00001`, `PCK-2026-00003`

**Scadenza tessera:** sempre **30 giugno** dell'anno di fine anno sportivo.
Anno sportivo `2026-2027` → scadenza `2027-06-30`.

### M02 — Calendario Palasirio

| Method | Path | Auth | Descrizione |
|---|---|---|---|
| `GET` | `/calendario` | pubblico | Lista slot con filtri (`data_inizio`, `data_fine`, `fascia`, `giorno_settimana[]`) |
| `GET` | `/calendario/{id}` | pubblico | Dettaglio singolo slot |
| `GET` | `/calendario/riepilogo-selezione` | autenticato | Calcolo prezzo server-side per slot selezionati |
| `GET` | `/calendario/ati-feed` | API Key | Feed ATI: solo `data`, `fascia`, `stato`, `is_nft_slot` |

**Calcolo prezzo (sempre server-side):**

```
ore_selezionate_notte     × €15 +
ore_selezionate_mattina   × €20 +
ore_selezionate_pomeriggio × €18
= totale_eur
```

**Esempio:** 2h mattina + 3h pomeriggio = (2×20) + (3×18) = **€94**

**Feed ATI — autenticazione:**

```bash
curl -H "X-API-Key: <ATI_API_KEY>" \
     https://millennioasd.com/api/v1/calendario/ati-feed
```

La chiave ATI ha una data di scadenza (`ATI_API_KEY_EXPIRES_AT`). Il backend logga un warning automatico 30 giorni prima della scadenza.

**Stati slot calendario:**

| Stato | Colore UI | Selezionabile | Descrizione |
|---|---|---|---|
| `libero` | Blu | ✅ | Disponibile per acquisto NFT |
| `nft_venduto` | Verde | ❌ | Venduto come NFT |
| `ati_occupato` | Grigio chiaro | ❌ | Slot ATI — sola lettura |
| `bloccato` | Arancio | ❌ | Lock ottimistico pre-mint (30 min) |

> **Regola critica:** Qualsiasi tentativo di modifica di uno slot con `associazione = 'ati'` restituisce **HTTP 403** indipendentemente dal ruolo del chiamante.

### M04-NFT — Raccolta fondi Palasirio

| Method | Path | Auth | Descrizione |
|---|---|---|---|
| `POST` | `/nft/acquisto` | `socio` (tessera attiva) | Avvia acquisto: lock slot → Stripe Session |
| `GET` | `/nft/verify` | `staff` | Verifica accesso QR: `?token_id=42&slot_key=2027-03-02_mattina` |
| `GET` | `/nft/dashboard` | `dirigenza` | Dashboard fundraising in tempo reale |

**Request body `/nft/acquisto`:**

```json
{
  "slot_ids": ["uuid1", "uuid2"],
  "acquisto_per_minore": false,
  "minore_id": null
}
```

**Response `/nft/acquisto`:**

```json
{
  "stripe_checkout_url": "https://checkout.stripe.com/pay/cs_...",
  "acquisto_id": "uuid",
  "importo_eur": 94.00,
  "lock_scadenza": "2027-03-02T10:30:00Z"
}
```

**Pre-condizioni acquisto NFT (verificate sia frontend che backend):**
- Socio autenticato con JWT valido
- Tessera con stato `attiva`
- Almeno uno slot selezionato
- Slot in stato `libero` (non `bloccato`, `nft_venduto`, `ati_occupato`)

### Webhooks Stripe

| Method | Path | Auth | Descrizione |
|---|---|---|---|
| `POST` | `/webhooks/stripe` | Firma HMAC | Gestisce eventi Stripe |

**Eventi gestiti:**

| Evento | Azione |
|---|---|
| `checkout.session.completed` | Verifica pagamento → `esegui_mint_task.delay()` |
| `payment_intent.payment_failed` | Log warning |
| `charge.refunded` | Log info (rimborso manuale da dirigenza) |

**Idempotency:** ogni `webhook_id` viene registrato in `WebhookLog`. Richieste duplicate restituiscono `{"status": "already_processed"}` senza ri-eseguire il mint.

### Rate Limiting

| Endpoint | Limite |
|---|---|
| `/nft/acquisto` | 10 req/min |
| `/tessere/{id}/pdf` | 10 req/min |
| `/nft/verify`, `/calendario/riepilogo-selezione`, ecc. | 30 req/min |
| `/calendario` (lista) | 60 req/min |
| `/webhooks/stripe` | 200 req/min |
| Default | 200 req/min |

Superato il limite: `HTTP 429 Too Many Requests`.
Storage Redis — se Redis non risponde, il limiter degrada silenziosamente (fail_open).

### Formato risposta errore

```json
{
  "error": "CODICE_ERRORE",
  "message": "Messaggio leggibile in italiano",
  "details": {}
}
```

---

## 7. Smart contract

### PalasirioNFT.sol

**Rete:** Polygon Amoy (testnet, chain ID 80002) → Polygon PoS (mainnet, chain ID 137)
**Standard:** ERC-721 + ERC721URIStorage + ERC721Enumerable + Ownable + IPalasirioNFT
**Caratteristica chiave:** Soulbound-like — trasferimenti bloccati; solo il contratto può trasferire (pattern escrow → socio al momento del mint).

**Funzioni principali:**

```solidity
// Mint base (senza registrazione slot on-chain)
mintNFT(address to, string memory uri) external onlyMinter returns (uint256)

// Mint avanzato con hash iCal e slot key registrati on-chain
mintNFTWithSlot(address to, string memory uri, string memory slotKey, string memory icalHash)
    external onlyMinter returns (uint256)

// Query
getTokensByOwner(address owner) external view returns (uint256[] memory)
isSlotBooked(string memory slotKey) external view returns (bool)

// Gestione minter
addMinter(address minter) external onlyOwner
removeMinter(address minter) external onlyOwner
```

**Evento on-chain:**

```solidity
event SlotBooked(
    uint256 indexed tokenId,
    address indexed member,
    string icalHash,
    string slotKey
);
```

### Setup smart contract

```bash
cd asd-millennio-contracts
npm install
```

Copia e compila il file `.env`:

```bash
cp .env.example .env
# Compila:
# PRIVATE_KEY=<wallet deployer>
# ALCHEMY_API_KEY=<chiave Alchemy>
# POLYGONSCAN_API_KEY=<chiave per verifica>
```

```bash
# Compila
npm run compile

# Test con coverage
npm test
npx hardhat coverage

# Deploy su Amoy testnet
npm run deploy:amoy

# Verifica sorgente su Polygonscan Amoy
npm run verify:amoy
```

**Requisiti di qualità (non derogabili per go-live):**
- Test coverage ≥ 95% (linee e funzioni), ≥ 90% branch
- Deploy su Amoy per almeno **30 giorni** di test prima del mainnet
- **Audit esterno obbligatorio** prima del deploy in produzione
- Contratto verificato e sorgente pubblico su Polygonscan

---

## 8. Test

### Backend — test unitari

```bash
cd asd-millennio-backend

# Crea e attiva venv (se non già fatto)
python -m venv .venv && source .venv/bin/activate

# Installa dipendenze dev
pip install -r requirements-dev.txt

# Esegui tutti i test unitari
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/millennio \
REDIS_URL=redis://localhost:6379/0 \
KEYCLOAK_URL=http://localhost:8080 \
KEYCLOAK_REALM=millennio-asd \
KEYCLOAK_CLIENT_ID=millennio-backend \
KEYCLOAK_CLIENT_SECRET=test \
JWT_SECRET=test-secret \
APP_URL=http://localhost:3000 \
  python -m pytest src/tests/unit/ -v --noconftest --tb=short

# Con coverage
python -m pytest src/tests/unit/ --cov=src --cov-report=term-missing \
  --noconftest -v
```

**Risultati attesi (Tier 1 — 30 test):**

| File | Test | Cosa copre |
|---|---|---|
| `test_soci_service.py` | 12 | Scadenza tessera, GDPR erasure, minori, consensi, pdf_url, permessi |
| `test_calendario_service.py` | 8 | Tariffe, ore slot, prezzo mix fasce, lock ATI (403), slot venduto (409) |
| `test_pdf.py` | 3 | PDF bytes validi, magic byte `%PDF`, tutti e 4 gli sport |
| `test_seed.py` | 4 | 130 giorni ATI, solo Tue/Thu/Sat, 16 slot/giorno (8+5+3) |
| `test_wallet.py` | 2 | AES-256-GCM round-trip, indirizzi unici |

```
30 passed in ~4s
```

### Backend — linting e formatting

```bash
cd asd-millennio-backend

# Linting (ruff)
ruff check src/

# Formatting check
black --check src/

# Fix automatico
black src/
ruff check src/ --fix
```

### Smart contract — test Hardhat

```bash
cd asd-millennio-contracts
npm test

# Con coverage (richiesto ≥ 95% lines/functions, ≥ 90% branches per CI)
npx hardhat coverage
```

### Frontend — type check e lint

```bash
cd asd-millennio-frontend
npm install
npx tsc --noEmit
npm run lint
npm run build
```

### Test end-to-end locale (flusso completo acquisto NFT)

> Richiede tutte le variabili d'ambiente configurate: Stripe test mode, Alchemy Amoy, Pinata.

```bash
# 1. Avvia l'intera stack
docker compose up -d

# 2. Applica migrazioni e seed
docker compose exec backend alembic upgrade head
docker compose exec backend python src/scripts/seed_slot_calendario.py

# 3. Avvia Stripe CLI per forwarding webhook in locale
stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe

# 4. Registra STRIPE_WEBHOOK_SECRET stampato da stripe listen nel .env

# 5. Login dal frontend → seleziona slot → acquista → completa pagamento Stripe test
# Card di test: 4242 4242 4242 4242 | exp: qualsiasi futura | CVC: qualsiasi

# 6. Verifica mint avvenuto
docker compose logs celery-worker -f

# 7. Verifica Token ID su Polygonscan Amoy:
# https://amoy.polygonscan.com/token/<CONTRACT_ADDRESS>
```

---

## 9. CI/CD

Ogni repository ha il proprio workflow GitHub Actions in `.github/workflows/ci.yml`.

### Backend CI (`.github/workflows/ci.yml`)

**Trigger:** push su `main`/`develop`, PR verso `main`

```
lint (ruff + black) → pytest (cov ≥ 80%) → docker build
```

**Secrets richiesti in GitHub:**

| Secret | Descrizione |
|---|---|
| `WALLET_ENCRYPTION_KEY_TEST` | Chiave AES-256 per i test (32 byte hex) |

### Frontend CI

```
npm lint → tsc --noEmit → next build
```

### Contracts CI

```
hardhat compile → hardhat test → coverage ≥ 95% lines/functions
```

### Deploy in produzione (via SSH su Hetzner)

Il deploy zero-downtime avviene servizio per servizio — mai `docker compose down`:

```bash
# Pull nuova immagine e restart solo del backend
docker compose pull backend && docker compose up -d --no-deps backend

# Pull e restart Celery worker (separato dal backend)
docker compose pull celery-worker && docker compose up -d --no-deps celery-worker

# Applica eventuali nuove migrazioni PRIMA di restartare il backend
docker compose exec backend alembic upgrade head
```

---

## 10. Deploy in produzione

### Struttura sul server Hetzner

```
/opt/millennio-asd/
├── docker-compose.yml      ← orchestrazione (non in repo — sul server)
├── .env                    ← segreti produzione (mai in repo)
├── nginx/
│   └── millennioasd.com.conf
└── backups/                ← dump PostgreSQL giornalieri
```

### Checklist pre-deploy

- [ ] `NODE_ENV=production` nel `.env`
- [ ] `APP_URL=https://millennioasd.com`
- [ ] `JWT_SECRET` e `WALLET_ENCRYPTION_KEY` generati con `secrets.token_hex(32)`
- [ ] `STRIPE_SECRET_KEY` in live mode (`sk_live_...`)
- [ ] `STRIPE_WEBHOOK_SECRET` da webhook endpoint produzione Stripe dashboard
- [ ] `MINTER_PRIVATE_KEY` gestita tramite KMS/Vault (non in `.env` in produzione)
- [ ] Certificato TLS Let's Encrypt via certbot attivo
- [ ] Backup volume PostgreSQL abilitato (Hetzner Snapshots, retention 7)
- [ ] Audit esterno smart contract completato
- [ ] DPIA (Data Protection Impact Assessment) completata per M01 e M04-NFT
- [ ] UAT superato: ≥ 3 utenti reali per profilo (socio, staff, dirigenza)

### Configurazione nginx (reverse proxy)

```nginx
server {
    listen 443 ssl http2;
    server_name millennioasd.com;

    ssl_certificate     /etc/letsencrypt/live/millennioasd.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/millennioasd.com/privkey.pem;
    ssl_protocols       TLSv1.3;

    # Backend API
    location /api/ {
        proxy_pass         http://backend:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        # Timeout generoso per l'upload IPFS durante il mint
        proxy_read_timeout 90s;
    }

    # Webhook Stripe — body raw necessario per verifica firma HMAC
    location /api/v1/webhooks/stripe {
        proxy_pass         http://backend:8000;
        proxy_set_header   Host $host;
        proxy_set_header   stripe-signature $http_stripe_signature;
        proxy_buffering    off;
    }

    # Frontend Next.js
    location / {
        proxy_pass         http://frontend:3000;
        proxy_set_header   Host $host;
    }

    # Health check interno (non esposto pubblicamente)
    location /health {
        proxy_pass  http://backend:8000/health;
        access_log  off;
    }
}

# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name millennioasd.com staging.millennioasd.com;
    return 301 https://$host$request_uri;
}
```

### Keycloak in produzione

Usa `start` (non `start-dev`) e configura:

```bash
KC_HOSTNAME=millennioasd.com
KC_PROXY=edge
KC_HTTP_ENABLED=true    # nginx gestisce TLS
KC_DB=postgres
KC_DB_URL=jdbc:postgresql://postgres:5432/millennio
```

---

## 11. Infrastruttura Hetzner

### Risorse MVP

| Risorsa | Tipo | Uso |
|---|---|---|
| App server | CX32 (4 vCPU, 8 GB RAM) | Backend + Frontend + Keycloak + Celery |
| Volume persistente | 40 GB | PostgreSQL data + backup locali |
| Load Balancer | LB11 | HTTPS termination, routing HTTP/HTTPS |
| Firewall | Hetzner Cloud Firewall | Solo 443/80 pubblici |

**Data center preferito:** FSN1 (Falkenstein) o NBG1 (Norimberga) — latenza minima dall'Italia, GDPR UE.

### Regole firewall (obbligatorie)

```
Inbound pubblico:  TCP 443, TCP 80 (solo dal Load Balancer)
Inbound SSH:       TCP 22 (solo da IP fissi del team — whitelist)
Inbound interno:   Tutto il traffico sulla rete privata Hetzner

Outbound:          Tutto consentito (necessario per Polygon RPC, Pinata, Stripe, Resend)
```

### Rete privata

- Tutti i servizi (postgres, redis, backend, keycloak) sulla rete privata Hetzner
- PostgreSQL e Redis **mai raggiungibili dall'IP pubblico**
- Solo il Load Balancer espone la porta 443/80 pubblicamente

### Backup

```bash
# Backup manuale PostgreSQL
docker compose exec postgres pg_dump -U postgres millennio | gzip \
  > /opt/millennio-asd/backups/millennio_$(date +%Y%m%d_%H%M%S).sql.gz

# Cron giornaliero (consigliato: 02:00 UTC)
0 2 * * * /opt/millennio-asd/scripts/backup.sh

# Retention: 90 giorni locale + 7 snapshot Hetzner automatici
```

---

## 12. Sicurezza e compliance

### GDPR

| Principio | Implementazione |
|---|---|
| Minimizzazione dati | NFT metadati: solo `asd_member_id` (numero tessera), mai CF/email/nome |
| Diritto alla cancellazione (Art. 17) | `DELETE /soci/{id}` → pseudoanonimizzazione (record preservato per audit blockchain) |
| Consensi | Entità `Consenso` con versione testo, timestamp firma, traccia revoche |
| Minori | Flag `is_minor`, tutore obbligatorio, doppio consenso, acquisto NFT solo dal tutore |
| Dati at-rest | AES-256 per chiavi private wallet custodiali |
| Dati in-transit | TLS 1.3 su tutti i canali |
| Audit log | `AccessoLog` immutabile per ogni verifica QR (ISO 27001) |

### Sicurezza applicativa

| Rischio | Mitigazione |
|---|---|
| Algorithm confusion JWT | PyJWT RS256 con PyJWKClient — algoritmi HS256/none rifiutati |
| CVE in python-jose | Migrato a PyJWT ≥ 2.8.0 (Sprint 3) |
| Double-mint (idempotency) | `WebhookLog` su `stripe_session_id` — unico in DB |
| Doppio pagamento → doppio mint | `stripe_session_id` UNIQUE su `AcquistoNFT` |
| Prezzo manipolato dal client | Prezzo sempre calcolato server-side in `calcola_prezzo()` |
| Slot doppia vendita | Lock ottimistico DB — `bloccato_fino_a` verificato prima del lock |
| Slot ATI modificati | HTTP 403 hardcoded indipendentemente dal ruolo |
| DDoS / brute force | slowapi rate limiting per IP, Redis-backed |
| CORS in produzione | Solo `https://millennioasd.com` — localhost escluso se `NODE_ENV=production` |
| Dati carta lato server | Mai gestiti — solo Stripe Checkout hosted page |
| Chiave minter in produzione | KMS/Vault obbligatorio — non in variabili d'ambiente |

### Compliance periodica

| Attività | Frequenza |
|---|---|
| Vulnerability assessment (OWASP Top 10) | Semestrale |
| Penetration test | Annuale |
| Audit smart contract | Prima del deploy mainnet |
| Rotazione chiavi API (ATI, JWT) | Annuale o su sospetto di compromissione |
| DPIA aggiornata | Prima di ogni nuovo modulo con dati personali |
| Data breach → GDPR Art. 33 | Notifica Garante entro 72h |

---

## 13. Rotazione chiavi e segreti

### ATI API Key

```bash
# 1. Genera nuova chiave
NEW_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 2. Aggiorna .env sul server (fuori orario di picco)
# ATI_API_KEY=<NEW_KEY>
# ATI_API_KEY_EXPIRES_AT=<YYYY-MM-DD>  ← nuova scadenza

# 3. Comunica la nuova chiave all'ATI con congruo anticipo
# 4. Restart backend
docker compose up -d --no-deps backend
```

> Il backend logga automaticamente un WARNING 30 giorni prima della scadenza della chiave ATI.

### WALLET_ENCRYPTION_KEY

⚠️ La rotazione di questa chiave richiede la ri-cifratura di tutte le chiavi private dei wallet custodiali. **Non ruotare senza un piano di migrazione dati.**

```bash
# Procedura:
# 1. Genera nuova chiave
NEW_ENC_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
# 2. Esegui script di migrazione (da sviluppare prima della rotazione)
# 3. Aggiorna .env e restart
```

### JWT_SECRET

```bash
# JWT_SECRET è usato solo come fallback interno — il sistema usa JWKS Keycloak.
# Ruotare aggiornando .env e restartando il backend.
NEW_JWT=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### Keycloak Client Secret

1. Console Keycloak → **Clients** → `millennio-backend` → **Credentials** → **Regenerate**
2. Copia il nuovo valore in `.env` come `KEYCLOAK_CLIENT_SECRET`
3. Restart backend: `docker compose up -d --no-deps backend`

---

## 14. Troubleshooting

### Backend non si avvia

```bash
# Verifica log
docker compose logs backend --tail=50

# Problemi comuni:
# 1. DATABASE_URL non raggiungibile → verifica postgres healthy
docker compose ps postgres

# 2. Keycloak JWKS non raggiungibile → il backend parte ma i JWT falliscono
# Verifica: curl http://localhost:8080/realms/millennio-asd/protocol/openid-connect/certs

# 3. Variabile d'ambiente mancante → verifica .env
docker compose exec backend python -c "from core.config import get_settings; print(get_settings())"
```

### Mint NFT fallisce (Celery)

```bash
# Verifica log worker
docker compose logs celery-worker -f

# Verifica stato task nel broker Redis
docker compose exec redis redis-cli
> KEYS celery-task-meta-*
> GET celery-task-meta-<task-id>

# Il task ha max 3 retry con backoff esponenziale (30s → 60s → 120s).
# Dopo il 3° fallimento: acquisto → stato 'fallito', slot → 'libero'.
# Log CRITICAL in celery-worker indicano intervento manuale richiesto.
```

### Webhook Stripe — 400 "Firma webhook non valida"

```bash
# Causa 1: STRIPE_WEBHOOK_SECRET errato o mancante
# → Verifica che il secret corrisponda all'endpoint registrato su Stripe

# Causa 2: Body modificato da proxy (buffering)
# → Verifica che nginx non bufferizzi il body (proxy_buffering off per /webhooks/stripe)

# Causa 3: Sviluppo locale senza stripe-cli
stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe
# Il CLI stampa il STRIPE_WEBHOOK_SECRET — aggiornalo nel .env
```

### Slot in stato "bloccato" dopo pagamento fallito

I lock scadono automaticamente dopo 30 minuti. Se un lock è rimasto attivo:

```bash
# Query SQL per verificare slot bloccati scaduti
docker compose exec postgres psql -U postgres millennio -c \
  "SELECT id, data, fascia, stato, bloccato_fino_a FROM slot_calendario
   WHERE stato = 'bloccato' AND bloccato_fino_a < NOW();"

# Il backend rilascia automaticamente i lock scaduti al primo GET /calendario
# oppure con la funzione release_slots()
```

### Test unitari — `ModuleNotFoundError: No module named 'pkg_resources'`

Causato dalla versione di `web3` installata globalmente che usa la vecchia API setuptools.

```bash
# Soluzione: usa il virtualenv del progetto
cd asd-millennio-backend
python -m venv .venv
source .venv/bin/activate        # o .venv\Scripts\Activate.ps1 su Windows
pip install -r requirements-dev.txt
```

### Keycloak — "Audience JWT non valida"

Il campo `audience` nel JWT deve corrispondere a `KEYCLOAK_CLIENT_ID` (`millennio-backend`).

```bash
# Verifica che il client abbia l'audience mapper configurato:
# Console Keycloak → Clients → millennio-backend → Client scopes
# → millennio-backend-dedicated → Mappers → Add mapper
# → Audience → Included Client Audience: millennio-backend
```

### Rate limit — 429 in sviluppo locale

```bash
# Il rate limiter usa l'IP remoto. In sviluppo con proxy può rilevare 127.0.0.1.
# Per disabilitare temporaneamente in sviluppo, impostare un limite molto alto in .env
# oppure svuotare i contatori Redis:
docker compose exec redis redis-cli FLUSHDB
```

---

## 15. Decisioni architetturali

| Decisione | Scelta | Motivazione |
|---|---|---|
| **Framework backend** | FastAPI (async) | Team Python, async nativo per blockchain + Stripe webhook latency variabile |
| **JWT validation** | PyJWT ≥ 2.8 (sostituisce python-jose) | Fix algorithm confusion CVE presenti in python-jose ≤ 3.3.0 |
| **Task queue** | Celery con `task_acks_late=True` | Ack dopo completamento — nessun mint perso in caso di crash worker |
| **Mint asincrono** | Celery + backoff esponenziale | Pinata + blockchain hanno latenza variabile; non bloccare il webhook handler |
| **PDF tessera** | Generato on-the-fly (reportlab) | Nessuna gestione filesystem, nessuna pulizia, UUID non indovinabile come URL |
| **GDPR erasure** | Pseudoanonimizzazione vs hard delete | FK constraints su record NFT + audit blockchain richiedono conservazione del record |
| **Prezzo NFT** | Sempre server-side | Il frontend non può inviare il prezzo — calcolato e verificato solo in `calcola_prezzo()` |
| **Lock slot** | Ottimistico con TTL 30min | Bilancio tra UX (slot visivamente riservati) e correttezza (rilascio automatico se pagamento non arriva) |
| **Wallet custodiale** | Default per tutti i soci | Nessuna conoscenza di blockchain richiesta al socio per l'MVP |
| **Blockchain** | Polygon PoS | Gas bassi, EVM-compatibile, ecosistema maturo per NFT |
| **Storage NFT** | IPFS via Pinata + backup DB | `ical_content` + `metadati_json` salvati off-chain prima dell'upload IPFS per resilienza |
| **Rate limiting** | slowapi + Redis (fail_open) | Se Redis non risponde, non blocca il servizio — degradazione silenziosa |
| **CORS produzione** | Solo `APP_URL` — no localhost | Sicurezza: localhost escluso automaticamente se `NODE_ENV=production` |

---

## 16. Roadmap fuori scope MVP

I seguenti moduli sono documentati nel PRD v1.1 ma esclusi dall'MVP (Release 1):

| Modulo | Descrizione |
|---|---|
| **M04-STD** | Raccolta fondi standard (donazioni, crowdfunding, sponsor) |
| **M05** | Archivio social media |
| **M06** | Comunicazione automatizzata (newsletter, notifiche push) |
| **M07** | Contabilità civica Flussocrazia |
| **M08** | AI Agent Framework |
| **M09** | Quality Dashboard |
| **M10** | Document Management |
| **Flussocrazia Civica** | Tornesi, NFT fondativi, fondo Bitcoin, socio-flussi |

> Se trovi riferimenti a questi moduli nel codice, segnalarlo — non implementare senza conferma esplicita.

---

## Contatti e risorse

| Riferimento | Link / Info |
|---|---|
| PRD v1.1 | Documento interno ASD Millennio |
| ERC-721 standard | https://eips.ethereum.org/EIPS/eip-721 |
| OpenZeppelin v5 | https://docs.openzeppelin.com/contracts/5.x/ |
| Stripe Checkout | https://stripe.com/docs/payments/checkout |
| Polygon Amoy testnet | https://amoy.polygonscan.com |
| RFC 5545 iCalendar | https://www.rfc-editor.org/rfc/rfc5545 |
| Hetzner Cloud docs | https://docs.hetzner.com/cloud |
| Resend docs | https://resend.com/docs |
| GDPR Art. 17 | https://gdpr-info.eu/art-17-gdpr/ |
| GDPR Art. 35 (DPIA) | https://gdpr-info.eu/art-35-gdpr/ |

---

*Ultima modifica: Maggio 2026 — ASD Millennio Dev Team*
*Allineato a CLAUDE.md + PRD v1.1 + Sprint 1–3 completati*
