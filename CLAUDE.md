# CLAUDE.md — ASD Millennio MVP

> Questo file è letto da Claude Code all'avvio. Seguilo sempre integralmente.
> Aggiornalo se le decisioni architetturali cambiano.

---

## 1. Contesto del progetto

Stai lavorando all'MVP della piattaforma digitale dell'**ASD Millennio**, un'associazione
sportiva dilettantistica (volley, badminton, kung fu, pickleball) che gestisce l'impianto
**Palasirio**.

**Documento di riferimento principale:** PRD v1.1 (ASD Millennio — Piattaforma di Gestione
Integrata). Ogni decisione tecnica deve essere coerente con quel documento.

**Scope dell'MVP (Release 1 — mesi 1–6):**
- M01 — Tesseramento e gestione soci
- M02 — Calendario e prenotazione Palasirio
- M03 — Autenticazione e IAM
- M04-NFT — Raccolta fondi Palasirio (NFT ERC-721 con iCal + Stripe)

**Fuori scope per ora — NON implementare:**
- Sistema Flussocrazia Civica (Tornesi, NFT fondativi, fondo Bitcoin, socio-flussi)
- M04-STD Raccolta fondi standard (donazioni, crowdfunding, sponsor)
- M05 Archivio social media
- M06 Comunicazione automatizzata
- M07 Contabilità civica
- M08 AI Agent Framework
- M09 Quality Dashboard
- M10 Document Management

Se trovi riferimenti a questi moduli nel codice o nei task, ignorali e segnalalo.

**Decisioni di progetto fissate:**

| Parametro | Valore | Note |
|---|---|---|
| Dominio produzione | `millennioasd.com` | Attualmente su Hetzner; migrazione da Aruba completata |
| Dominio staging | `staging.millennioasd.com` | Sottodominio sullo stesso server Hetzner |
| Keycloak realm | `millennio-asd` | Usa questo nome ovunque — inclusi redirect URI |
| Anno sportivo corrente | `2026-2027` | Usato nei seed DB e nella logica tessere |
| Scadenza tessera | 30 giugno di ogni anno | Fine anno sportivo — non rolling |
| Obiettivo raccolta fondi | env var `FUNDRAISING_TARGET_EUR` | Valore default `300000` (€300.000) |
| NFT per acquisto | Un solo NFT con tutti gli slot scelti | Mai un NFT per singolo slot |
| Prezzo NFT | Pricing dinamico server-side | Tariffe base: Notte €15/h · Mattina €20/h · Pomeriggio €25/h — poi moltiplicatori dinamici |
| Deploy | Docker Compose su Hetzner | Vedi Sezione 3.2 |
| Email transazionali | Resend | Vedi Sezione 6 variabili d'ambiente |

---

## 2. Struttura repository

Il progetto usa **repo separate**. Quando lavori su un task, sei sempre dentro una di queste:

```
asd-millennio-frontend/     # React / Next.js
asd-millennio-backend/      # API server FastAPI — vedi Sezione 4
asd-millennio-contracts/    # Solidity / Hardhat
```

Non creare mai file di un'altra repo nella repo corrente.
Se un task richiede modifiche su più repo, completane una alla volta e segnala le dipendenze.

---

## 3. Stack tecnologico — MVP

### 3.1 Tabella stack

| Layer | Tecnologia | Note |
|---|---|---|
| Frontend | React + Next.js | SSR abilitato; componenti in `/components` |
| Styling | Tailwind CSS | Nessun CSS custom salvo casi eccezionali |
| Backend | FastAPI (Python ≥ 3.12) | Asincrono, tipizzato con Pydantic, OpenAPI auto-generata |
| Database | PostgreSQL | Migrazioni in `src/migrations/` (Alembic) con numerazione sequenziale |
| Cache / sessioni | Redis | Solo sessioni e cache breve, non dati permanenti |
| Autenticazione | Keycloak | SSO, MFA, ruoli; non reinventare auth da zero |
| Blockchain | Polygon (MATIC) | Testnet: Amoy; Mainnet: Polygon PoS |
| Smart contract | Solidity + OpenZeppelin ERC-721 | Hardhat per test e deploy |
| IPFS | Pinata | Per metadati NFT e file iCal |
| Pagamenti | Stripe Checkout + Webhooks | Mai gestire dati carta lato server |
| Cloud | Hetzner Cloud (Falkenstein / Norimberga / Helsinki) | Data residency UE obbligatoria — vedi Sezione 3.2 |
| CI/CD | GitHub Actions | Pipeline in `.github/workflows/` |
| Monitoraggio | Grafana + Prometheus + Sentry | Configurazione minima nell'MVP |

### 3.2 Infrastruttura Hetzner — configurazione MVP

Il progetto usa **Hetzner Cloud** come provider. Data center: preferibilmente
**Falkenstein (FSN1)** o **Norimberga (NBG1)** per latenza minima dall'Italia;
in alternativa **Helsinki (HEL1)**. Tutti e tre sono in territorio UE (GDPR compliant).

**Risorse Hetzner previste per l'MVP:**

| Risorsa | Tipo consigliato | Uso |
|---|---|---|
| App server | CX32 (4 vCPU, 8 GB RAM) | Backend API + Next.js |
| DB server | CX22 (2 vCPU, 4 GB RAM) | PostgreSQL — volume separato |
| Cache server | CX11 (2 vCPU, 2 GB RAM) | Redis |
| Volume persistente | ≥ 40 GB | Dati PostgreSQL + backup locali |
| Load balancer | Hetzner LB11 | HTTPS termination + routing |
| Firewall | Hetzner Cloud Firewall | Regole: solo 443/80 pubblici |

**Regole obbligatorie per Hetzner:**
- Tutti i server in **rete privata Hetzner (Private Network)** — nessun servizio
  esposto direttamente su IP pubblico tranne il load balancer
- PostgreSQL e Redis **mai raggiungibili dall'esterno** — solo dalla rete privata
- Backup automatici Hetzner abilitati su tutti i volumi (retention 7 snapshot)
- Firewall Hetzner: porta 22 (SSH) aperta solo a IP fissi del team di sviluppo
- Usa **Hetzner DNS** o Cloudflare per gestione DNS + protezione DDoS

**Nodo Polygon:**
- Per il nodo RPC Polygon non serve un server dedicato nell'MVP:
  usa un provider RPC esterno (Alchemy, QuickNode, o Infura) con endpoint HTTPS.
  Se in futuro si vuole un nodo Polygon proprio, aggiungere un server separato.

**CI/CD su Hetzner:**
- GitHub Actions deploya via SSH sul server app (usando secrets GitHub)
- Mai esporre la porta SSH su IP pubblici non autorizzati
- Deploy con Docker Compose: `docker compose pull && docker compose up -d --no-deps --build {service}`
- `docker-compose.yml` nella root del server, gestisce: `backend`, `frontend`, `postgres`, `redis`
- Zero-downtime: restart per servizio, non `down` + `up` dell'intera stack

**Monitoring:**
- Grafana + Prometheus installati sullo stesso app server nell'MVP (separare in R2)
- Hetzner Cloud Metrics come backup per CPU/RAM/disco
- Alert su Sentry per errori applicativi

### 3.3 Backend — FastAPI (Python ≥ 3.12) ✅ decisione confermata

Il backend usa **FastAPI** con Python 3.12+. La scelta è definitiva per l'MVP.

**Motivazioni:**
- Il team ha competenze Python consolidate — zero curva di apprendimento sul linguaggio
- FastAPI è asincrono nativamente (`async/await`) — fondamentale per webhook Stripe
  e chiamate blockchain (web3.py) che possono avere latenza variabile
- Tipizzazione forte con **Pydantic v2** — modelli di dati validati automaticamente
- Documentazione OpenAPI auto-generata su `/docs` — utile con frontend JS separato
- Ecosystem Python maturo per crypto: `web3.py`, `eth-account`, `cryptography`

**Librerie principali:**

| Libreria | Versione | Uso |
|---|---|---|
| `fastapi` | ≥ 0.111 | Framework principale |
| `uvicorn` | ≥ 0.29 | ASGI server (con `--workers` in prod) |
| `pydantic` | v2 | Validazione modelli e settings |
| `sqlalchemy` | ≥ 2.0 (async) | ORM con supporto async |
| `alembic` | ≥ 1.13 | Migrazioni DB |
| `asyncpg` | ≥ 0.29 | Driver PostgreSQL asincrono |
| `redis` | ≥ 5.0 (async) | Client Redis asincrono |
| `stripe` | ≥ 9.0 | SDK Stripe ufficiale Python |
| `web3` | ≥ 6.0 | Interazione smart contract Polygon |
| `eth-account` | ≥ 0.11 | Gestione wallet custodiali |
| `cryptography` | ≥ 42.0 | Cifratura AES-256 chiavi private |
| `python-jose` | ≥ 3.3 | Validazione JWT Keycloak |
| `httpx` | ≥ 0.27 | Client HTTP asincrono |
| `celery` | ≥ 5.3 | Task asincroni (email, alert scadenze tessere) |
| `pytest-asyncio` | ≥ 0.23 | Test asincroni |

**Convenzioni FastAPI obbligatorie:**
- Usa sempre `async def` per gli endpoint — mai `def` sincrono
- Dependency injection per DB session: `db: AsyncSession = Depends(get_db)`
- Dependency injection per utente corrente: `user = Depends(get_current_user)`
- Router separato per ogni modulo, incluso in `main.py` con prefisso `/api/v1/`
- Modelli Pydantic separati per input (Request) e output (Response) — mai esporre
  il modello ORM direttamente nella risposta
- Gestione eccezioni centralizzate con `@app.exception_handler`
- Mai usare `def` sincrono per operazioni I/O (DB, HTTP, blockchain, IPFS)

---

## 4. Moduli MVP — dettaglio operativo

### M03 — Autenticazione e IAM (prerequisito di tutto)

Implementa per primo. Tutto il resto dipende da questo.

**Ruoli Keycloak da configurare:**

| Ruolo | Permessi chiave |
|---|---|
| `socio` | Self-service: profilo, tessera, acquisto NFT (se tessera attiva) |
| `allenatore` | Presenze, calendario, comunicazioni atleti |
| `staff` | Tesseramento, registro NFT, verifica accessi Palasirio |
| `dirigenza` | Report, dashboard fundraising, pricing, rendiconto, approvazioni |
| `pubblico` | Solo lettura pagine pubbliche |

**Regole obbligatorie:**
- MFA obbligatorio per `staff` e `dirigenza`
- SSO con Google e Apple per `socio`
- Gestione minori: account associato al tutore legale, flag `is_minor: true`,
  nessuna operazione autonoma del minore senza consenso tutore
- Audit log immutabile su ogni accesso e modifica dati sensibili (ISO 27001)

---

### M01 — Tesseramento e gestione soci

**Entità principale: `Socio`**

```
id                UUID PRIMARY KEY
nome              VARCHAR NOT NULL
cognome           VARCHAR NOT NULL
data_nascita      DATE NOT NULL
codice_fiscale    VARCHAR(16) UNIQUE NOT NULL
indirizzo         TEXT
email             VARCHAR UNIQUE NOT NULL
telefono          VARCHAR
foto_url          TEXT
is_minor          BOOLEAN DEFAULT false
tutore_id         UUID REFERENCES socio(id)   -- obbligatorio se is_minor
sport             VARCHAR[]                    -- ['volley','badminton','kung_fu','pickleball']
created_at        TIMESTAMPTZ DEFAULT now()
updated_at        TIMESTAMPTZ DEFAULT now()
```

**Entità: `Tessera`**

```
id                UUID PRIMARY KEY
socio_id          UUID REFERENCES socio(id)
numero_tessera    VARCHAR UNIQUE NOT NULL      -- prefisso sport + progressivo
sport             VARCHAR NOT NULL
stato             ENUM('bozza','in_attesa_pagamento','attiva','scaduta','sospesa')
data_emissione    DATE
data_scadenza     DATE
anno_sportivo     VARCHAR                      -- es. '2026-2027'
pdf_url           TEXT                         -- tessera digitale con QR
created_at        TIMESTAMPTZ DEFAULT now()
updated_at        TIMESTAMPTZ DEFAULT now()
```

**Regole business:**
- Numero tessera: `{PREFISSO_SPORT}-{ANNO_INIZIO}-{PROGRESSIVO_5_CIFRE}`
  dove `ANNO_INIZIO` è il primo anno dell'anno sportivo (es. anno sportivo `2026-2027` → `2026`).
  Esempi: `VOL-2026-00042`, `BDM-2026-00007`, `KFU-2026-00001`, `PCK-2026-00003`
- **Categoria "sostenitore"**: `Tessera.sport = 'sostenitore'` (stessa colonna, nessuna migration), prefisso
  `SOS` (`SOS-2026-00001`). Non è un ruolo Keycloak, è una categoria di tessera. Il gate d'acquisto NFT
  resta "tessera attiva" (sport *o* sostenitore) — invariato. Si diventa sostenitore in due modi, **mai per
  donazione** (erogazioni liberali sono M04-STD, fuori scope): (a) automaticamente, alla conferma di un
  acquisto NFT — emessa/rinnovata sul **socio pagante** (mai sul minore, anche per acquisti
  `acquisto_per_minore`), idempotente per anno sportivo; (b) emissione manuale da staff per sostenitori
  senza tessera sportiva. Un socio può avere sport + sostenitore insieme. Prezzo NFT invariato.
- **Auto-tesseramento self-service (primo accesso)**: al primo login (Keycloak, registrazione aperta a
  tutti) se non esiste un profilo `Socio` (`/soci/me` → 404) il frontend porta al wizard onboarding.
  Flusso **ibrido paga→provvisoria→verifica**: anagrafica + upload **documento d'identità** + consenso
  (adulto: privacy+trattamento; minore: doppio consenso privacy/trattamento + foto_video, firmati dal
  tutore) + **pagamento quota** (Stripe) → tessera **`attiva` provvisoria** (`verifica_stato=in_verifica`,
  scadenza +30gg). Lo **staff** conferma entro 30gg (`GET/POST /soci/verifiche…`); se rifiuta, la tessera
  decade (`sospesa`) e la quota **non è rimborsata** ma marcata **erogazione liberale** (flag minimo su
  `pagamento_tessera`, non il modulo M04-STD). Nessuna azione a 30gg → **auto-conferma** (Celery beat, silenzio-assenso).
  Le **quote** sono gestite dalla dirigenza (`quote_tessera`, `GET/POST/PUT /dirigenza/quote-tessera`), variabili
  per categoria (sport/sostenitore) e adulto/minore. Documenti sensibili **cifrati AES-256** su volume privato
  (`documenti_data`), scaricabili solo da proprietario/tutore/staff. **Minori**: aggiunti dal tutore
  (`POST /soci/me/minori`), senza login proprio (email sintetica), gestiti dal tutore. CF validato col checksum.
- Alert automatici scadenza: 30, 15, 7 giorni prima (email + notifica push)
- Un socio può avere tessere per sport diversi nello stesso anno
- Scadenza tessera: sempre il **30 giugno** dell'anno sportivo corrente, indipendentemente
  dalla data di emissione. Anno sportivo corrente: `2026-2027` → scadenza `2027-06-30`.
  Al rinnovo, emettere nuova tessera per anno `2027-2028` → scadenza `2028-06-30`.
- Workflow emissione: `bozza → in_attesa_pagamento → attiva`
- Solo soci con tessera `attiva` possono acquistare NFT Palasirio
- Tessera digitale PDF (PRD §RF-M01-002): generata automaticamente all'emissione,
  deve contenere un QR code che punta a `GET /api/v1/tessere/{id}/verifica` (endpoint pubblico).
  Il PDF viene salvato su storage e il link aggiornato in `pdf_url`.
- Importazione massiva da CSV/Excel per migrazione dati iniziali:
  endpoint `POST /api/soci/import` con validazione e report errori

**Consensi GDPR — entità `Consenso`:**

Regole critiche (PRD §RF-M01-003):
- Maggiorenni: un solo consenso con firma elettronica semplice
- Minorenni: doppio consenso obbligatorio —
  1. firma del tutore legale (tipo `privacy` + `trattamento_dati`)
  2. autorizzazione specifica per ogni attività (tipo `foto_video`, ecc.)
- Nessuna operazione su dati del minore senza entrambi i consensi attivi
- Il registro consensi deve tracciare: timestamp, versione del testo, revoche

```
id                UUID PRIMARY KEY
socio_id          UUID REFERENCES socio(id)
tipo              ENUM('privacy','trattamento_dati','foto_video','marketing')
testo_versione    VARCHAR                      -- hash o versione del testo
firmato_da        UUID REFERENCES socio(id)    -- tutore se minore
timestamp_firma   TIMESTAMPTZ
revocato_at       TIMESTAMPTZ                  -- null se attivo
```

---

### M02 — Calendario e Palasirio

**Periodo di vendita NFT Palasirio:** `2027-01-01` → `2042-12-31` (env: `CALENDARIO_INIZIO` / `CALENDARIO_FINE`)

**Fasce orarie disponibili per la vendita NFT:**
- Giorni: **Lunedì, Martedì, Mercoledì, Giovedì, Venerdì**
- Sabato e domenica: **non vendibili** — non presenti nel sistema
- Ore commercializzabili: **00:00 – 14:59** (15 ore per giorno)

| Fascia | Orario | Durata | Tariffa base |
|---|---|---|---|
| Notte | 00:00 – 07:59 | 8 ore | **€15/ora** |
| Mattina | 08:00 – 12:59 | 5 ore | **€20/ora** |
| Pomeriggio | 13:00 – 14:59 | 2 ore | **€25/ora** |

**Totale ore vendibili per settimana: 75** (15h × 5 giorni)

**Calcolo prezzo NFT — regola definitiva:**
Il prezzo è calcolato per **ora selezionata** con pricing dinamico server-side.
Il frontend non calcola mai i prezzi — riceve dal backend il `prezzo_ora_corrente`
per ogni fascia al momento della selezione.

Formula:
```
prezzo_ora_finale = tariffa_base × moltiplicatore_data × moltiplicatore_scarsità × (1 - sconto_promo)
```

Esempi con tariffe base:
- 3 ore di mattina (base) → 3 × €20 = **€60**
- 8 ore di notte (base) → 8 × €15 = **€120**
- 2 ore pomeriggio (base) → 2 × €25 = **€50**
- Mix: 2h mattina + 2h pomeriggio (base) → (2×€20) + (2×€25) = **€90**

Il calcolo avviene **sempre server-side** (FastAPI) prima di creare la Stripe Session.

**Motore di pricing dinamico — regole obbligatorie:**

**Leva 1 — Prossimità alla data** (applicata per prima):

| Giorni mancanti alla data | Moltiplicatore default |
|---|---|
| > 60 giorni | × 1.00 |
| 30 – 60 giorni | × 1.10 |
| 15 – 30 giorni | × 1.20 |
| 7 – 15 giorni | × 1.35 |
| < 7 giorni | × 1.50 |

**Leva 2 — Scarsità ore disponibili** (applicata sul risultato della leva 1):

| % ore ancora libere nella fascia | Moltiplicatore default |
|---|---|
| > 75% libere | × 1.00 |
| 50 – 75% libere | × 1.10 |
| 25 – 50% libere | × 1.25 |
| < 25% libere | × 1.40 |

**Sconto promozionale** (applicato per ultimo):
- Percentuale configurabile dalla dashboard dirigenza
- Attivabile/disattivabile con toggle (campo `attivo`)
- Può essere limitato a una fascia specifica, un giorno specifico o globale
- Ha una data di scadenza opzionale (`valido_fino_a`)
- Se più sconti attivi si sovrappongono, si applica il più alto

**Tutti i parametri di pricing** (tariffe base, soglie, moltiplicatori, sconti) sono
configurabili dalla dashboard dirigenza senza toccare il codice — vedi tabella `pricing_rules`.

**Entità: `SlotCalendario`**

```
id                UUID PRIMARY KEY
data              DATE NOT NULL
fascia            ENUM('notte','mattina','pomeriggio')
ora_inizio        TIME NOT NULL                -- ora esatta di inizio fascia (es. 08:00)
ora_fine          TIME NOT NULL                -- ora esatta di fine fascia (es. 12:59)
ore_totali        SMALLINT NOT NULL            -- ore totali della fascia (8, 5, o 2)
ore_vendute       INTEGER[]  DEFAULT '{}'      -- array ore vendute es. [8,9,10] = mattina parziale
stato             ENUM('libero','parziale','esaurito','bloccato')
nft_token_id      INTEGER                      -- ultimo token_id che ha acquistato ore in questo slot
bloccato_fino_a   TIMESTAMPTZ                  -- scadenza lock (30 min dal blocco)
created_at        TIMESTAMPTZ DEFAULT now()
updated_at        TIMESTAMPTZ DEFAULT now()
```

Stato calcolato:
- `libero` → `ore_vendute` è vuoto
- `parziale` → alcune ore vendute, altre libere
- `esaurito` → tutte le ore vendute
- `bloccato` → lock temporaneo durante flusso pagamento (max 30 min)

**Entità: `PricingRule`** (gestita dalla dirigenza)

```
id               UUID PRIMARY KEY
tipo             ENUM('tariffa_base','leva_data','leva_scarsita','sconto_promo')
fascia           ENUM('notte','mattina','pomeriggio') NULL  -- null = tutte le fasce
soglia_min       NUMERIC(8,2)    -- giorni mancanti OPPURE % disponibile OPPURE tariffa
soglia_max       NUMERIC(8,2)
valore           NUMERIC(8,4)    -- moltiplicatore o percentuale sconto
attivo           BOOLEAN DEFAULT true
nome             VARCHAR         -- etichetta leggibile (es. "Black Friday -20%")
valido_fino_a    DATE            -- null = nessuna scadenza (per sconti promo)
note             TEXT
created_at       TIMESTAMPTZ DEFAULT now()
updated_at       TIMESTAMPTZ DEFAULT now()
```

**Regole slot:**
- Lock ottimistico pre-pagamento: le ore selezionate vengono bloccate durante il flusso
  di pagamento per evitare doppia vendita (max 30 minuti)
- Se un'ora è già in `ore_vendute` di un altro acquisto, il backend rifiuta con HTTP 409
- Export iCal standard (`RFC 5545`) per Google Calendar / Outlook
- Verifica disponibilità sempre server-side prima di accettare la selezione dal frontend

**Colori UI calendario:**
- 🔵 Blu: ora libera — selezionabile
- 🟢 Verde: ora già venduta come NFT — NON selezionabile, tooltip "già prenotata"
- 🟠 Arancio: ora in lock da altro acquirente — NON selezionabile temporaneamente
- ⬜ Grigio: ora fuori dalle fasce vendibili (≥ 15:00) o fuori dai giorni (sab/dom)

**Filtri rapidi del selettore (calendario frontend):**
- Per giorno della settimana: Lunedì / Martedì / Mercoledì / Giovedì / Venerdì
- Per fascia oraria: Notte / Mattina / Pomeriggio
- Per periodo: tutto il periodo / settimana corrente / giorni pari / giorni dispari
- Click su fascia → seleziona tutte le ore libere di quella fascia
- Click su singola ora → seleziona/deseleziona quell'ora specifica
- Riepilogo live: ore selezionate per fascia, prezzo/ora corrente (da backend), totale

**Regola UI critica:** il frontend verifica la disponibilità di ogni ora via API prima di
permettere la selezione. Non fidarsi mai dello stato cached lato client per gli slot.

**Endpoint calendario:**
```
GET /api/v1/calendario                              → lista slot con stato e prezzo corrente
GET /api/v1/calendario/disponibilita                → ore libere con prezzo_ora per ogni fascia
POST /api/v1/calendario/lock                        → blocca ore selezionate (pre-pagamento)
GET /api/v1/calendario/riepilogo-selezione          → totale e dettaglio ore selezionate
```

---

### M04-NFT — Raccolta fondi Palasirio

Questo è il modulo più critico dell'MVP. Segui il flusso end-to-end con precisione.

#### 4.0 Pre-condizioni acquisto NFT (PRD §RF-M04NFT-001)

Il pulsante "Acquista come NFT" nel frontend deve essere:
- **Disabilitato** se il socio non è autenticato → mostrare "Accedi per acquistare"
- **Disabilitato** se il socio non ha tessera `attiva` → mostrare "Tessera non attiva"
- **Disabilitato** se nessuna ora è selezionata
- **Attivo** solo se: autenticato + tessera attiva + almeno un'ora selezionata

Il backend verifica nuovamente queste condizioni server-side al momento del mint
(non fidarsi solo del frontend).

#### 4.1 Flusso tecnico completo

```
1. Socio autentica (Keycloak) → verifica tessera attiva
2. Socio seleziona ore nel calendario interattivo (fascia intera o singole ore)
3. Frontend chiama backend → verifica disponibilità ore per ora
4. Sistema applica lock ottimistico sulle ore selezionate (max 30 min)
5. Backend calcola prezzo con motore dinamico (leva_data × leva_scarsità × sconto_promo)
6. Sistema genera file iCal (.ics) con VEVENT per ogni ora selezionata
7. Sistema carica metadati JSON su IPFS (Pinata) con iCal in base64
8. Smart contract ERC-721 minta NFT con URI → metadati IPFS
   (NFT in escrow fino a pagamento confermato)
9. Socio paga tramite Stripe Checkout (hosted page)
10. Webhook Stripe `checkout.session.completed` → backend conferma pagamento
11. Backend verifica pagamento anche con Stripe API retrieve (doppia verifica)
12. Smart contract trasferisce NFT al wallet del socio (custodial di default)
13. Ore aggiornate in `ore_vendute` dello SlotCalendario
14. Email al socio: iCal scaricabile + Token ID + link Polygonscan
```

Se il pagamento non arriva entro 30 minuti dal lock → rilascia il lock (ore tornano libere).

**Vincolo di performance (PRD §14.2):** l'intero flusso selezione → iCal → IPFS → mint
deve completarsi in **meno di 60 secondi** dal click su "Acquista".
Se supera i 60s, log dell'errore + notifica all'utente + rilascio del lock.

#### 4.2 File iCal — formato obbligatorio

Un VEVENT per ogni **ora** acquistata (non per fascia):

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ASD Millennio//Palasirio//IT
BEGIN:VEVENT
UID:{uuid-univoco}@millennioasd.com
DTSTART:{YYYYMMDD}T{HH0000}
DTEND:{YYYYMMDD}T{HH+10000}
SUMMARY:Diritto d'uso Palasirio — {fascia} — ASD Millennio
DESCRIPTION:Token ID: {token_id} | Socio: {tessera_id} | Verifica: polygonscan.com/token/{contract}/{token_id}
STATUS:CONFIRMED
END:VEVENT
...un VEVENT per ogni ora acquistata...
END:VCALENDAR
```

Genera SHA-256 del file iCal completo → incluso nei metadati NFT per verifica integrità.

#### 4.3 Metadati NFT — formato ERC-721 (standard OpenSea/IPFS)

```json
{
  "name": "Diritto d'uso Palasirio — {N} ore — ASD Millennio",
  "description": "Questo token NON è uno strumento finanziario ai sensi della Direttiva MiFID II. Rappresenta esclusivamente il diritto d'uso del Palasirio per le ore specificate. Non garantisce rendimenti economici.",
  "attributes": [
    { "trait_type": "Ore totali", "value": "{N}" },
    { "trait_type": "Data primo slot", "value": "{YYYY-MM-DD}" },
    { "trait_type": "Fascia oraria", "value": "{notte|mattina|pomeriggio}" },
    { "trait_type": "Valore pagato (€)", "value": "{importo}" }
  ],
  "ical_content": "{base64_del_file_ics}",
  "ical_sha256": "{hash_sha256}",
  "asd_member_id": "{numero_tessera}",
  "legal_disclaimer": "Diritto d'uso personale e non trasferibile. Subordinato al mantenimento della qualità di socio attivo ASD Millennio."
}
```

#### 4.4 Smart contract — PalasirioNFT.sol

Usa OpenZeppelin come base. Requisiti obbligatori:

```solidity
// Estendi: ERC721, ERC721URIStorage, ERC721Enumerable, Ownable
// Rete: Polygon Amoy (testnet) → Polygon PoS (mainnet)

// Funzioni obbligatorie:
mintNFT(address to, string memory tokenURI) external onlyMinter
tokenURI(uint256 tokenId) public view override returns (string memory)
getTokensByOwner(address owner) external view returns (uint256[] memory)
isSlotBooked(string memory slotKey) external view returns (bool)

// Trasferibilità BLOCCATA (Soulbound-like):
// Override transferFrom, safeTransferFrom → revert sempre

// Evento obbligatorio:
event SlotBooked(uint256 indexed tokenId, address indexed member, string icalHash, string slotKey);
```

**Requisiti di qualità smart contract:**
- Test coverage ≥ 95% con Hardhat
- Deploy su testnet Amoy per almeno 30 giorni prima del mainnet
- Audit esterno obbligatorio prima del deploy in produzione
- Contratto verificato e pubblicato su Polygonscan (sorgente pubblico)

#### 4.5 Entità DB — `AcquistoNFT`

```
id                  UUID PRIMARY KEY
socio_id            UUID REFERENCES socio(id)
stripe_session_id   VARCHAR UNIQUE NOT NULL
stripe_payment_id   VARCHAR
token_id            INTEGER UNIQUE
contract_address    VARCHAR
ipfs_uri            VARCHAR
ical_sha256         VARCHAR
importo_eur         NUMERIC(10,2) NOT NULL
ore_acquistate      INTEGER[]               -- array ore acquistate es. [8,9,13,14]
stato               ENUM('in_attesa_pagamento','pagato','mintato','fallito','rimborsato')
acquisto_per_minore BOOLEAN DEFAULT false
minore_id           UUID REFERENCES socio(id)
wallet_address      VARCHAR
metadati_json       TEXT                    -- backup off-chain metadati IPFS
ical_content        TEXT                    -- backup off-chain file .ics
created_at          TIMESTAMPTZ DEFAULT now()
updated_at          TIMESTAMPTZ DEFAULT now()
```

Relazione: un `AcquistoNFT` è collegato a uno o più `SlotCalendario` tramite tabella
`acquisto_nft_slots (acquisto_nft_id, slot_calendario_id, ore_acquistate INTEGER[])`.

#### 4.6 Wallet custodiale

- Il backend genera un wallet Ethereum per ogni socio al momento del primo acquisto
- Chiave privata cifrata con AES-256, mai esposta in chiaro
- Conservata nel DB cifrato, isolata per socio
- Il socio interagisce solo con l'interfaccia ASD, mai con il wallet direttamente

#### 4.7 Integrazione Stripe

- Usa sempre **Stripe Checkout hosted page** (mai form custom lato ASD)
- Il prezzo viene calcolato **server-side** prima di creare la Session
- Webhook endpoint: `POST /api/v1/webhooks/stripe`
  - Verifica firma webhook con `STRIPE_WEBHOOK_SECRET`
  - Gestisci: `checkout.session.completed`, `payment_intent.payment_failed`, `charge.refunded`
  - Idempotency: registra ogni `webhook_id` processato per evitare doppi mint

**Politica rimborsi:** il token è non rimborsabile per scelta del socio.
Eccezione: se l'ASD cancella il diritto d'uso → stato `rimborsato`, ore → libere, email al socio.

**Contenuto obbligatorio ricevuta email:**
- Riepilogo ore acquistate (date, fasce, ore totali, prezzo pagato per ora)
- Token ID assegnato on-chain
- Link download file iCal
- Link verifica NFT su Polygonscan
- Dichiarazione legale MiFID II

#### 4.8 Dashboard fundraising — dirigenza (`/dirigenza`)

Infografica in tempo reale (aggiornamento < 5 secondi dopo ogni pagamento):

**Sezione 1 — Riepilogo raccolta:**
- Progress bar verso obiettivo `FUNDRAISING_TARGET_EUR` (default €300.000)
- Totale raccolto (€) e percentuale completamento
- Numero NFT emessi totali
- Ore vendute / ore disponibili per fascia (Notte / Mattina / Pomeriggio)
- % di riempimento per fascia con indicatore visivo

**Sezione 2 — Andamento vendite:**
- Grafico a barre: incassi degli ultimi 30 giorni
- Top 5 fasce più vendute (data + fascia + importo)
- Mappa calendario occupazione Palasirio (slot NFT in verde, liberi in blu)

**Sezione 3 — Export:**
- CSV/PDF storico completo: socio (pseudonimizzato), ore, importo, data, Token ID

#### 4.9 Dashboard pricing — dirigenza (`/dirigenza/pricing`)

Gestione completa del motore di pricing senza toccare il codice:

- **Tabella tariffe base**: modifica tariffa oraria per fascia (notte/mattina/pomeriggio)
- **Leva data**: modifica soglie in giorni e moltiplicatori
- **Leva scarsità**: modifica soglie in % e moltiplicatori
- **Sconti promozionali**: crea/attiva/disattiva sconti con nome, %, fascia target, data scadenza
- **Simulatore prezzi**: inserisci data + % disponibilità → vedi prezzo ora risultante per fascia
- **Storico modifiche**: timestamp + utente per ogni modifica alle regole

Endpoint backend:
```
GET    /api/v1/dirigenza/pricing-rules         → lista regole attive [RequireDirigenza]
POST   /api/v1/dirigenza/pricing-rules         → crea regola
PUT    /api/v1/dirigenza/pricing-rules/{id}    → modifica regola
DELETE /api/v1/dirigenza/pricing-rules/{id}    → disattiva regola
GET    /api/v1/dirigenza/pricing-simulate      → simula prezzo dato data + disponibilità
```

#### 4.10 Rendiconto annuale — dirigenza (`/dirigenza/rendiconto`)

- Selezione anno sportivo
- Ore 00:00–14:59 vendute nell'anno, per fascia
- Ricavi lordi totali
- Export PDF certificato (con logo ASD Millennio, data stampa, anno di riferimento)
- Entro il 30 giugno di ogni anno

Endpoint backend:
```
GET  /api/v1/dirigenza/rendiconto?anno=2026   → dati rendiconto annuale [RequireDirigenza]
GET  /api/v1/dirigenza/rendiconto/pdf?anno=2026 → PDF scaricabile
```

#### 4.11 Verifica accesso al Palasirio (staff)

**Entità DB — `AccessoLog`** (audit ISO 27001):
```
id              UUID PRIMARY KEY
token_id        INTEGER NOT NULL
socio_id        UUID REFERENCES socio(id)
slot_key        VARCHAR NOT NULL
verificato_da   UUID REFERENCES socio(id)
esito           ENUM('valido','non_valido','slot_errato','tessera_scaduta')
checked_at      TIMESTAMPTZ DEFAULT now()
note            TEXT
```

App staff per verifica QR:
- `GET /api/v1/nft/verify?token_id={id}&slot_key={data_fascia_ora}`
- Risponde: `{ valid: bool, socio: string, slot: object, checked_at: timestamp }`
- Risposta in < 2 secondi
- Ogni accesso verificato registrato (audit ISO 27001)

---

## 5. Sicurezza — regole non derogabili

### 5.1 Dati personali e GDPR

- **Mai** esporre dati personali in URL
- **Mai** loggare dati personali (CF, email, data nascita) nei log applicativi
- **Mai** scrivere dati personali on-chain: solo hash pseudonimizzati
- Il collegamento `Token ID ↔ Socio` esiste solo nel DB interno (cifrato, cancellabile)
- Minori: accesso ai dati solo da tutore legale, istruttore assegnato, staff autorizzato
- Consensi GDPR: verificati prima di qualsiasi operazione su dati personali

### 5.2 Autenticazione e accessi

- Principio del minimo privilegio: ogni ruolo vede solo i dati necessari
- MFA obbligatorio per `staff` e `dirigenza` — non bypassabile
- Token JWT con scadenza breve (access: 15min, refresh: 7gg)
- Audit log immutabile per tutti gli accessi a dati sensibili

### 5.3 Pagamenti e blockchain

- **Mai** gestire dati carta lato server ASD — sempre Stripe hosted
- Il prezzo viene sempre calcolato server-side, mai accettato dal client
- Doppia verifica pagamento: webhook Stripe + Stripe API retrieve
- Nessun mint avviene prima della conferma di pagamento
- Chiavi private wallet: AES-256, mai in chiaro, mai nei log
- Chiave minter: in HSM o KMS in produzione. In dev/staging: `.env` con `MINTER_PRIVATE_KEY`

### 5.4 Cifratura

- Dati at-rest: AES-256 per tutti i dati personali
- Dati in-transit: TLS 1.3 su tutti i canali
- Backup giornaliero cifrato, retention 90 giorni

### 5.5 Audit e compliance periodica

- Vulnerability assessment semestrale (OWASP Top 10)
- Penetration test annuale
- Incident response: data breach notificato entro 72h (GDPR Art. 33)
- DPIA obbligatoria per M01 e M04-NFT prima del go-live

---

## 6. Variabili d'ambiente

Non hardcodare mai questi valori nel codice. Usa sempre le variabili d'ambiente.
Crea sempre un file `.env.example` con i nomi (senza valori reali).

```bash
# Database
DATABASE_URL=

# Redis
REDIS_URL=

# Keycloak
KEYCLOAK_URL=
KEYCLOAK_REALM=millennio-asd
KEYCLOAK_CLIENT_ID=
KEYCLOAK_CLIENT_SECRET=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PUBLISHABLE_KEY=

# Blockchain
POLYGON_RPC_URL=
POLYGON_CHAIN_ID=                  # 80002 testnet Amoy, 137 mainnet
CONTRACT_ADDRESS_PALASIRIO_NFT=
MINTER_PRIVATE_KEY=                # mai committare questo valore

# IPFS / Pinata
PINATA_API_KEY=
PINATA_SECRET_KEY=
PINATA_GATEWAY_URL=

# Crypto wallet custodiale
WALLET_ENCRYPTION_KEY=             # AES-256 key per cifrare chiavi private soci

# Email — Resend
RESEND_API_KEY=
EMAIL_FROM=noreply@millennioasd.com

# App
NODE_ENV=
APP_URL=https://millennioasd.com
JWT_SECRET=
HETZNER_API_TOKEN=

# Business logic
FUNDRAISING_TARGET_EUR=300000             # obiettivo raccolta fondi (€300.000)
ANNO_SPORTIVO_CORRENTE=2026-2027
TESSERA_SCADENZA_MESE=6
TESSERA_SCADENZA_GIORNO=30

# Periodo vendita slot Palasirio (inclusivo)
CALENDARIO_INIZIO=2027-01-01
CALENDARIO_FINE=2042-12-31

# Pricing — tariffe base (override del seed DB, usate solo al primo avvio)
TARIFFA_BASE_NOTTE=15
TARIFFA_BASE_MATTINA=20
TARIFFA_BASE_POMERIGGIO=25
```

---

## 7. Convenzioni di codice

### Generali
- Lingua del codice: **inglese** (variabili, funzioni, commenti tecnici)
- Lingua dei messaggi utente e log leggibili: **italiano**
- Backend Python: segui **PEP 8** — usa `black` per formatting, `ruff` per linting
- Frontend JS/TS: usa **ESLint + Prettier** con config progetto
- Nessun `print()` o `console.log` in produzione — usa il logger configurato
- Nessun `TODO` o `FIXME` committato senza issue tracker associata
- Nessuna dipendenza aggiunta senza motivazione esplicita nel commit

### Naming
- Database: `snake_case` per tabelle e colonne
- API: `kebab-case` per URL, `snake_case` per JSON body
- Python — variabili/funzioni: `snake_case`; classi: `PascalCase`; costanti: `UPPER_SNAKE_CASE`
- JavaScript/TypeScript — variabili/funzioni: `camelCase`; componenti React: `PascalCase`

### API REST
- Prefisso: `/api/v1/`
- Autenticazione: Bearer token JWT (da Keycloak)
- Risposta errore standard:
  ```json
  { "error": "CODICE_ERRORE", "message": "Messaggio leggibile", "details": {} }
  ```
- Sempre restituire HTTP status code semanticamente corretto
- Paginazione su tutte le liste: `?page=1&limit=20`

### Database
- Ogni migrazione in un file separato: `{timestamp}_{descrizione}.py` (Alembic)
- Nessuna migrazione distruttiva senza backup verificato
- Indici su tutte le foreign key e sui campi usati in WHERE frequenti
- `updated_at` aggiornato automaticamente con trigger su ogni tabella

### Test
- Backend: test unitari + integration test per ogni endpoint
- Smart contract: test Hardhat, coverage ≥ 95%
- Frontend: test componenti critici (flusso acquisto NFT, calendario)
- Nessun codice in produzione senza almeno un test sull'happy path
- Definition of Done: ogni modulo richiede UAT superato con almeno 3 utenti reali per profilo

---

## 8. Struttura directory attesa

### asd-millennio-backend/
```
src/
  main.py
  core/
    config.py
    security.py
    database.py
    redis.py
  modules/
    auth/
    soci/
    calendario/
      pricing.py       # motore pricing dinamico
    nft/
    dirigenza/         # dashboard, pricing rules, rendiconto
    webhooks/
  models/
  schemas/
  migrations/
  tests/
    unit/
    integration/
requirements.txt
requirements-dev.txt
.env.example
Dockerfile
```

### asd-millennio-frontend/
```
app/
  dashboard/           # area soci autenticati
    nft/               # acquisto NFT con nuovo CalendarioSelector
  staff/               # verifica accessi
  dirigenza/           # dashboard fundraising
    pricing/           # gestione regole pricing
    rendiconto/        # report annuale
components/
  calendario/          # CalendarioSelector (ora + fascia, pricing live)
  nft/
  soci/
  ui/
lib/
  api/
  auth/
  stripe/
.env.example
```

### asd-millennio-contracts/
```
contracts/
  PalasirioNFT.sol
  interfaces/
    IPalasirioNFT.sol
test/
  PalasirioNFT.test.js
scripts/
  deploy.js
  verify.js
hardhat.config.js
.env.example
```

---

## 9. Flussi critici — non improvvisare

1. **Acquisto NFT Palasirio** → Sezione 4.1 (flusso end-to-end, max 60 secondi)
2. **Verifica pagamento Stripe** → doppia verifica webhook + API retrieve (Sezione 4.7)
3. **Lock ore calendario** → lock ottimistico pre-pagamento, rilascio a 30min (Sezione 4.1)
4. **Pricing dinamico** → sempre calcolato server-side, mai accettato dal client (Sezione M02)
5. **Gestione minori** → flag `is_minor`, tutore obbligatorio, acquisto NFT solo dal tutore
6. **Wallet custodiale** → chiave cifrata AES-256, mai in chiaro (Sezione 4.6)
7. **Consensi GDPR minori** → doppio consenso obbligatorio prima di qualsiasi operazione
8. **Anti double-sell** → verifica `ore_vendute` server-side prima di ogni lock (HTTP 409 se ora già venduta)

---

## 10. Cosa fare quando non sai come procedere

1. **Decisione architetturale non coperta qui** → chiedi prima di scrivere codice
2. **Conflitto tra due approcci** → descrivi entrambi e chiedi
3. **Scopri un rischio di sicurezza** → segnalalo immediatamente prima di proseguire
4. **Task fuori scope MVP** → segnala che è fuori scope e chiedi conferma
5. **Smart contract: qualsiasi modifica non banale** → mostra il diff e chiedi approvazione

---

## 11. Riferimenti

| Documento | Descrizione |
|---|---|
| PRD v1.1 | Product Requirements Document completo ASD Millennio |
| ERC-721 standard | https://eips.ethereum.org/EIPS/eip-721 |
| OpenZeppelin ERC-721 | https://docs.openzeppelin.com/contracts/4.x/erc721 |
| Stripe Checkout docs | https://stripe.com/docs/payments/checkout |
| Polygon Amoy testnet | https://amoy.polygonscan.com |
| RFC 5545 iCalendar | https://www.rfc-editor.org/rfc/rfc5545 |
| Hetzner Cloud docs | https://docs.hetzner.com/cloud |
| Resend docs | https://resend.com/docs |
| GDPR Art. 35 (DPIA) | Valutazione d'impatto — obbligatoria prima del lancio |

---

*Ultima modifica: Giugno 2026 — ASD Millennio Team Dev — v2.0 (pricing dinamico, calendario Lun-Ven 00:00-15:00)*
