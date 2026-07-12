# HANDOFF — ASD Millennio MVP

> Passaggio di consegne auto-contenuto. **Aggiornato il 2026-07-12** · branch `fix/p0-payment-mint`.
> Leggere insieme a `CLAUDE.md` (intero) e alla memoria in
> `C:\Users\Romano\.claude\projects\F--millennio-flussocrazia\memory\` (`MEMORY.md` è l'indice).

# COS'È

- **Obiettivo**: MVP della piattaforma digitale dell'**ASD Millennio** (volley, badminton, kung fu, pickleball) che gestisce l'impianto **Palasirio**.
- **Cosa fa**: tesseramento soci, calendario/raccolta fondi tramite **NFT ERC-721** ("diritti d'uso" orari del Palasirio con iCal + Stripe + wallet custodiale), **prenotazione campi** badminton/pickleball, aree per ruolo (socio, staff, dirigenza) + sito pubblico.
- **Ruoli Keycloak**: `socio`, `allenatore`, `staff`, `dirigenza`, `pubblico`.
- **Scope MVP**: M01 Soci · M02 Calendario/Palasirio · M03 Auth · M04-NFT · (+) Prenotazione campi. **Fuori scope** (non implementare): Flussocrazia Civica, M04-STD, M05–M10.

# STATO ATTUALE (2026-07-12)

Stack **completo e funzionante in locale** (Docker Compose, tutti i container up). Base solida (P0–P3, rename Palasirio, carrello campi, area dirigenza) invariata; sopra è stata aggiunta molta roba in questa sessione.

**Novità sessione 2026-07-09 → 12 (tutto committato e pushato):**
- ✅ **Socio sostenitore** (`Tessera.sport='sostenitore'`, prefisso `SOS`): emesso automaticamente alla conferma di un acquisto NFT (sul socio pagante, mai sul minore), idempotente per anno. Commit `bb80f26`.
- ✅ **Certificato di sostegno PDF** (celebrativo A4, 2 pagine, **logo ASD Millennio** vettoriale via `svglib`) generato alla conferma del mint + **email Resend** (PDF+iCal) + pagina **"Il mio sostegno"** (`/dashboard/miei-nft`). Nuova colonna `acquisti_nft.mint_tx_hash`. Commit `6475779`, `29a706d`.
- ✅ **Auto-tesseramento self-service (adulti e minori)** — feature grande, 5 fasi, commit `f36d036`. Vedi §AUTO-TESSERAMENTO.
- 🐛 **Fix trovati in UAT** (dentro i commit sopra): webhook Stripe andava sempre in 500 (`dict(event)`/`.get()` incompatibili con stripe-python 15 → usa body grezzo + `.to_dict()`); lock ore NFT si auto-bloccava ad ogni acquisto (`consenti_gia_bloccato`); `campi._verifica_tessera` esplodeva con socio a 2 tessere attive (`scalars().first()`); carrello campi ottimistico (feedback immediato + toast); `APP_URL` allineato a `:3000`.

✅ **Committato e pushato** su `origin/fix/p0-payment-mint`: 4 nuovi commit (`bb80f26`, `6475779`, `29a706d`, `f36d036`) oltre a `efb8cdd`. Branch **11 commit avanti** su `main`. **PR NON ancora aperta** (`gh` non installato → aprirla a mano, form pre-compilato: https://github.com/romanobenit/Portale_Millennio/compare/main...fix/p0-payment-mint?expand=1).

# TECH STACK

- **Linguaggi**: Python 3.12, TypeScript, Solidity 0.8.24.
- **Backend**: FastAPI async, SQLAlchemy 2.0 async, Pydantic v2, Alembic, Celery 5.x.
- **Frontend**: Next.js 14 (App Router), React, Tailwind, axios, keycloak-js.
- **Smart contract**: Solidity + OpenZeppelin v5 (ERC721 + URIStorage + Enumerable + Ownable), Hardhat, solidity-coverage.
- **DB**: PostgreSQL 16 · **Cache/broker**: Redis 7 · **Auth**: Keycloak 24 (realm `millennio-asd`).
- **Blockchain**: Polygon Amoy testnet (chainId 80002), `web3.py` 7.16.0. **Pagamenti**: Stripe Checkout + webhook (chiavi test **funzionanti**, checkout verificato). **IPFS**: Pinata. **Email**: Resend (solo TODO).
- **Infra**: Docker Compose locale; target prod Hetzner (non fatto). RPC via Alchemy (Amoy).

# COME AVVIARE

Working dir: `F:\millennio\flussocrazia`. Shell: **PowerShell** (il `.bashrc` di Git Bash ha un errore di sintassi alla riga 1 → preferire PowerShell).

```powershell
# 1. Docker Desktop deve essere avviato (i dati Docker sono su F: — vedi §GOTCHA)
docker compose up -d
# 2. attendere: postgres fa il recovery e Keycloak ci mette ~1 min ad avviarsi.
#    Se postgres è 'unhealthy' aspettare la fine del fsync, poi rilanciare `up -d`.
docker compose ps        # tutti healthy
```

**Punti d'accesso**:
- App / area soci: **http://localhost:3000** (`/dashboard`) · area dirigenza: **/dirigenza**
- API + Swagger: **http://localhost:8000/docs**
- Keycloak admin: **http://localhost:8080/admin** (credenziali `KEYCLOAK_ADMIN`/`_PASSWORD` dal `.env`)

**Ricostruire dopo modifiche** (il codice è nell'immagine, no volume mount):
```powershell
docker compose build <backend|frontend> ; docker compose up -d <svc>
# frontend: se il build riusa una COPY cachata "sporca", usare --no-cache
```
**Spegnere pulito** (evita il lungo recovery di postgres al riavvio):
```powershell
docker compose stop
```

# ARCHITETTURA

Monorepo con 3 sotto-repo orchestrate da Docker Compose:
```
asd-millennio-backend/    (FastAPI + Celery)
asd-millennio-frontend/   (Next.js)
asd-millennio-contracts/  (Hardhat/Solidity)
docker-compose.yml + docker-compose.override.yml (gitignored: porte + KC_HOSTNAME_PORT/PROXY)
keycloak/realm-millennio-asd.json   (export del realm — vedi §KEYCLOAK)
```
**Servizi Docker**: `postgres`, `redis`, `keycloak`, `backend`, `frontend`, `celery-worker` (`-Q celery`), `celery-mint-worker` (`-Q mint --concurrency=1`, serializza il nonce on-chain).

**Moduli backend** (`src/modules/`): `soci` (M01, con Repository) · `calendario` (M02 + `pricing.py`) · `nft` (M04: `service`, `blockchain`, `ipfs`, `ical`, `wallet`) · `campi` (prenotazione campi, **modello carrello**) · `dirigenza` (fundraising, pricing rules, rendiconto, `campi_router` template) · `webhooks` (`stripe_handler`) · `tasks/mint.py` (Celery mint). Auth in `core/security.py` (JWT Keycloak via PyJWKClient).

# PRENOTAZIONE CAMPI (ridisegnata in questa sessione)

Da "prenota il blocco intero e paga subito" a **per-ora + carrello + pagamento unico**:
- Un `slot_template_campo` (finestra es. 16:30–19:30, `num_campi`, `costo_ora`) viene diviso in **slot da 1 ora**. La disponibilità è calcolata **per singola ora** (overlap sui campi occupati).
- **Carrello**: `POST /campi/carrello` blocca un'ora (lock 30 min, nessun pagamento) e assegna un campo libero. `GET /campi/carrello` lista le ore bloccate non scadute.
- **Pagamento unico**: `POST /campi/carrello/checkout` crea **una sola** sessione Stripe con più line item (una per ora) → tutte le prenotazioni condividono lo stesso `stripe_session_id`.
- **Conferma**: il webhook `checkout.session.completed` (tipo `prenotazione_campo`) → `conferma_pagamento(session_id)` conferma **tutte** le prenotazioni di quella sessione.
- **Auto-annullo "fine sessione"**: se non si paga, i lock scadono a 30 min; `_scadi_lock_socio` li marca `scaduta` (lazy, all'accesso al carrello) → campi liberati.
- **Cancellazione**: `DELETE /campi/prenota/{id}` — se `bloccata` la toglie dal carrello, se `confermata` la cancella (entro 24h prima).
- **Frontend** `app/dashboard/prenotazioni/page.tsx`: griglia compatta (card per giorno con chip orari), sezione carrello con totale + "Paga tutto", "Rimuovi" per riga. **Ogni pulsante = 1 chiamata = 1 azione** (verificato end-to-end).
- **Endpoint** (`/api/v1`): `GET /campi/disponibilita` (pubblico, per-ora) · `POST/GET /campi/carrello` · `POST /campi/carrello/checkout` · `GET /campi/le-mie-prenotazioni` (solo confermate) · `DELETE /campi/prenota/{id}`.

# KEYCLOAK (setup ricostruito)

Il realm era andato perso col DB → ricreato via API. **È stato esportato** in `keycloak/realm-millennio-asd.json` (ri-importabile con `--import-realm`); il DB però è volatile → se serve, ricreare.
- **Realm** `millennio-asd`; **client** `millennio-frontend` (public, PKCE S256, redirect `http://localhost:3000/*` e `:3100/*`); **ruoli** realm: `socio, allenatore, staff, dirigenza, pubblico`.
- **Registrazione self-service ATTIVA** + `socio` come **ruolo di default** (per sbloccare in dev — da disattivare per prod).
- **Fix issuer port-less**: nel `docker-compose.override.yml`, keycloak ha `KC_HOSTNAME_PORT: "8080"` + `KC_PROXY: none` (senza, il login POSTa su porta 80 → `ERR_CONNECTION_REFUSED`). Il backend **non** valida l'`iss` (solo firma via JWKS interno + audience), quindi lo split-hostname browser(`localhost:8080`)/backend(`keycloak:8080`) non dà problemi.
- **DB keycloak**: se manca (`FATAL: database "keycloak" does not exist`) → `docker exec ... psql -U postgres -c "CREATE DATABASE keycloak;"` + restart.
- **Utente di test**: `benito` (email `romanobenit@gmail.com`), ruoli **`dirigenza` + `socio`**. È collegato al socio DB **"Benito Romano"** (id `1c1c4d76-4c5a-41cc-9f99-4a69fa040bd3`, ex "Mario Rossi" seed) con **tessera volley attiva**. NB: i ruoli sono nel JWT → dopo un cambio ruolo serve **ri-login**.

# TOKEN / AUTH (fix di questa sessione)

- L'access token Keycloak dura **~5 min**. Prima le chiamate riusavano un token statico → dopo la scadenza tutto tornava **401**. Ora `lib/api/client.ts` (axios) chiama `updateToken(30)` **prima di ogni richiesta**; anche `app/dashboard/prenotazioni` e `dirigenza/campi` usano lo stesso refresh. Le pagine `/dirigenza` sono protette da `app/dirigenza/layout.tsx` (inizializza Keycloak + verifica ruolo + chrome condivisa; senza, `/dirigenza` respingeva alla home).
- **CORS**: aggiunto **`PUT`** a `allow_methods` in `main.py` (mancava → modifiche template/pricing andavano in "Failed to fetch").

# DATABASE

- DB `millennio` (+ `keycloak`). Tabelle: `soci`, `tessere`, `consensi`, `slot_calendario`, `pricing_rules`, `acquisti_nft` (+`acquisto_nft_slots`, `accesso_log`), `wallet_custodiali`, `webhook_log`, `slot_template_campo`, `prenotazioni_campo`.
- Relazioni: `acquisti_nft` —N:M via `acquisto_nft_slots(ore_acquistate INT[])`— `slot_calendario`; `tessere/wallet/acquisti/prenotazioni` → `soci`; `prenotazioni_campo` → `slot_template_campo`.
- Vincoli: `acquisti_nft.stripe_session_id` UNIQUE; `uq_acquisti_nft_contract_token UNIQUE(contract_address, token_id)`. **`prenotazioni_campo.stripe_session_id` NON è più UNIQUE** (rimosso per il carrello → indice normale).
- **Migrazioni Alembic (head = `20260711_140000`)**: `…` → `20260705_120000_drop_prenotazione_session_unique` → `20260711_120000_add_mint_tx_hash` (colonna `acquisti_nft.mint_tx_hash`) → **`20260711_140000_tesseramento_onboarding`** (campi verifica su `tessere`; nuove tabelle `documenti_socio`, `quote_tessera`, `pagamento_tessera`). Il DB in esecuzione è stampato a `20260711_140000`. Ricorda `alembic upgrade head` dopo un rebuild.
- **Nuove tabelle** (auto-tesseramento): `documenti_socio` (metadati documenti cifrati), `quote_tessera` (quote dirigenza), `pagamento_tessera` (pagamento quota Stripe; stato `erogazione_liberale` sui rifiuti). `tessere` ha ora `verifica_stato / verifica_scadenza / verificata_da / verificata_at`.
- `alembic` nel container: `docker exec <backend> sh -c "cd /app && alembic upgrade head"`.

# FUNZIONALITÀ IMPLEMENTATE

- **M03 Auth**: JWT Keycloak (PyJWKClient), ruoli, `RequireDirigenza/Staff/Socio`. **Login e2e funzionante.**
- **M01 Soci/Tessere**: CRUD, numero tessera (`FOR UPDATE`), PDF+QR, import CSV (savepoint/riga), consensi GDPR, verifica tessera pubblica, categoria **sostenitore** (§dedicata), **auto-tesseramento self-service** adulti+minori (§AUTO-TESSERAMENTO).
- **M02 Calendario/Pricing**: slot Lun-Ven 00:00–14:59, disponibilità con prezzo dinamico, lock 30 min, motore pricing (leva_data × scarsità-per-mese × sconto), simulatore, CRUD pricing rules.
- **M04-NFT**: acquisto→Stripe→webhook→mint, wallet custodiali AES-256-GCM, iCal+SHA-256, metadati IPFS, verifica accesso per-ora, dashboard fundraising (**fix query 30gg**), rendiconto annuale.
- **Certificato di sostegno (PDF)** — implementato 2026-07-11: alla conferma del mint viene generato un certificato celebrativo A4 (2 pagine: attestato con dati on-chain + Allegato A con elenco ore) e inviato via **Resend** con PDF + iCal in allegato. Scaricabile anche da **"I miei NFT"** (`/dashboard/miei-nft`). Backend: `modules/nft/certificato.py` (reportlab, disegno su canvas), `certificato_builder.py` (assembla da DB), `email.py` (Resend REST via httpx, no-op se `RESEND_API_KEY` vuota). Endpoint `GET /nft/le-mie` e `GET /nft/{id}/certificato` (owner o staff). Nuova colonna `acquisti_nft.mint_tx_hash` (migration `20260711_120000`) popolata dal worker; `mint_nft_with_slots` ora ritorna `(token_id, tx_hash)`. Token storici (pre-feature) mostrano "—" alla voce transazione di conio.
- **Contratto PalasirioNFT** (Amoy): `mintNFT`, `mintNFTWithSlots` (anti double-sell on-chain), `updateTokenURI/IcalHash`, `isSlotBooked`, `getTokenSlotKeys`, soulbound. **Deployato + verificato** su Amoy.
- **Prenotazione campi**: **per-ora + carrello** (vedi §dedicata).
- **Frontend**: sito pubblico (`app/(public)`), dashboard soci, area dirigenza (chrome condivisa: dashboard/pricing/rendiconto/campi + "Area soci"/"Sito pubblico"), staff verifica.

# SOCIO SOSTENITORE (IMPLEMENTATO — 2026-07-09)

Il "socio sostenitore" è una **categoria di tessera** (`Tessera.sport = 'sostenitore'`), non un ruolo Keycloak. Nessuna migration di schema: la colonna `sport` era già `String` libera.

**Regole implementate:**
- Prefisso numero tessera **`SOS`** (`SOS-2026-00001`) — `SPORT_PREFISSI` in [soci/service.py](asd-millennio-backend/src/modules/soci/service.py).
- **Gate acquisto NFT invariato**: serve una tessera attiva (sport *o* sostenitore); `_verifica_tessera_attiva` non è stato toccato.
- **Emissione automatica alla conferma NFT**: `NFTService._assicura_tessera_sostenitore(socio_id)` in [nft/service.py](asd-millennio-backend/src/modules/nft/service.py), chiamata da `conferma_pagamento` subito dopo `acquisto.stato = "pagato"`, **nella stessa transazione** del webhook (prima del `flush` finale). Idempotente per anno sportivo: se esiste già una tessera SOS per l'anno la riattiva (se non attiva) senza duplicarla; altrimenti la crea `attiva` da subito (nessun passaggio `bozza`/pagamento — è "inclusa" nell'acquisto NFT già pagato).
- **Acquisto per un minore → decisione confermata dall'utente**: il sostenitore è sempre il **socio pagante** (`acquisto.socio_id`), mai il minore, indipendentemente da `acquisto_per_minore`/`minore_id`.
- **Emissione manuale da staff**: resta possibile via `POST /soci/{socio_id}/tessere` con `sport="sostenitore"` (nessuna UI staff per l'emissione tessere esiste ancora nel frontend — è backend-only anche per gli altri sport, non è stato aggiunto nulla di nuovo qui).
- Etichetta "Socio Sostenitore" in `SPORT_LABEL`: [soci/pdf.py](asd-millennio-backend/src/modules/soci/pdf.py) (tessera PDF) e [dashboard/tessere/page.tsx](asd-millennio-frontend/app/dashboard/tessere/page.tsx) ("Le mie tessere"). Il componente `components/soci/TesseraCard.tsx` è **dead code** (non importato da nessuna pagina) — non toccato.
- Erogazioni liberali / donazioni restano ESCLUSE (M04-STD, fuori scope).
- `CLAUDE.md §M01` aggiornato con la regola.

**Verificato:**
- `pytest src/tests/unit/test_nft_service.py` — 10/10 (2 nuovi test: emissione + idempotenza; test 8 aggiornato per le query aggiuntive).
- Smoke reale contro il DB del container `backend` (script temporaneo, poi rimosso): prima chiamata crea `SOS-2026-00001` attiva con scadenza `2027-06-30` e `pdf_url`; seconda chiamata non duplica (1 sola riga).
- Immagine `backend` ricostruita e riavviata con il nuovo codice (`docker compose build backend && up -d backend`) — healthy, nessun errore di import.
- **Committato** in `bb80f26`.

# AUTO-TESSERAMENTO SELF-SERVICE (IMPLEMENTATO — 2026-07-12, commit `f36d036`)

Onboarding al primo accesso per chi deve tesserarsi (adulto) o tesserare un figlio minorenne. Flusso **ibrido: paga → attiva provvisoria → verifica staff** (decisioni concordate con l'utente).

**Flusso adulto**: login Keycloak (registrazione **aperta a tutti**) → `/soci/me` 404 → il `dashboard/layout` reindirizza al **wizard `/dashboard/onboarding`** (anagrafica + **upload documento identità** + consenso privacy/trattamento) → **paga la quota** (Stripe) → tessera **`attiva` provvisoria** (`verifica_stato='in_verifica'`, scadenza +30gg, accesso pieno ai benefici da subito).

**Flusso minore** (`/dashboard/minori`): il tutore aggiunge il figlio (`POST /soci/me/minori`, **nessun login proprio**, email sintetica) → upload **identità + tutela** + **doppio consenso** (privacy, trattamento, foto_video firmati dal tutore) → il tutore paga la quota minore.

**Verifica staff** (`/dirigenza/tesseramenti`): coda dei tesseramenti provvisori → **Conferma** oppure **Rifiuta**. Rifiuto = tessera `sospesa` + quota **erogazione liberale** (niente rimborso, flag su `pagamento_tessera`, NON il modulo M04-STD). **Nessuna azione a 30gg → auto-conferma** (silenzio-assenso) via **Celery beat** (`tasks/tesseramento.py`, worker con `-B`, ogni giorno 03:00).

**Quote** (`/dirigenza/quote`): gestite dalla dirigenza (`quote_tessera`), variabili per categoria (sport/sostenitore) e adulto/minore. ⚠️ **Senza almeno una quota attiva il tesseramento si blocca** con "Quota non configurata".

**Tecnica**: endpoint self `POST /soci/me`, `/me/documenti`, `/me/tesseramento`, `/me/minori(+/{id}/tesseramento)`; staff `GET/POST /soci/verifiche…`; dirigenza `GET/POST/PUT /dirigenza/quote-tessera`. Documenti sensibili **cifrati AES-256** (`core/storage.py`) su **volume Docker privato `documenti_data` → `/data/documenti`** (chiave `DOCUMENT_ENCRYPTION_KEY`, fallback `WALLET_ENCRYPTION_KEY`); download gated owner/tutore/staff. Validazione **checksum CF** (`modules/soci/codice_fiscale.py`). Branch webhook `tipo=tessera`. Service centrale: `modules/soci/tesseramento_service.py`. 24 unit test (`test_tesseramento.py`), tutte le 5 fasi verificate e2e nel container.

# GOTCHA / KNOWN ISSUES (aggiornati)

- **Auto-tesseramento — configurare le quote**: dopo il deploy, la dirigenza DEVE creare almeno una `quote_tessera` (pagina `/dirigenza/quote`), altrimenti l'onboarding fallisce con "Quota non configurata".
- **Nuovo volume `documenti_data`**: montato su `backend` (`/data/documenti`), contiene i documenti sensibili cifrati. Va incluso nei backup (con retention e cancellazione GDPR). `DOCUMENT_ENCRYPTION_KEY` in `.env` (o usa `WALLET_ENCRYPTION_KEY`).
- **Celery beat embedded (`-B`)**: l'auto-conferma gira sul `celery-worker` con beat embedded (worker singolo → nessun doppio scheduling). Schedule su `/tmp/celerybeat-schedule`.
- **`RESEND_API_KEY` vuota**: l'email del certificato (e le future notifiche) è un no-op finché la chiave non è impostata. Il PDF resta scaricabile.
- **Erogazione liberale**: implementata come flag minimo su `pagamento_tessera.stato`, NON è il modulo donazioni M04-STD (che resta fuori scope).

- **Docker su F:**: il disco C: si era riempito → la distro WSL2 `docker-desktop-data` (~50 GB) è stata spostata su `F:\DockerData\wsl\data`. Il `BasePath` nel registro (`HKCU\...\Lxss\{11aeb12d-...}`) punta lì. Se Docker non trova i dati, controllare quel BasePath. Cartella progetto e dati Docker sono entrambi su F:.
- **postgres lento all'avvio dopo riavvio PC**: fa recovery/fsync (60–160s) → Keycloak/backend aspettano. Se apri l'app subito → `ERR_EMPTY_RESPONSE`/401 vari. Aspettare ~1–2 min, oppure fare `docker compose stop` prima di spegnere il PC.
- **Frontend build — `.dockerignore`**: esiste `asd-millennio-frontend/.dockerignore` che esclude `node_modules`/`.next` MA **deve includere `.env.local`** (Next inlinea i `NEXT_PUBLIC_*`, tra cui l'URL Keycloak, a build-time). Se lo escludi → l'area soci va in "client-side exception".
- **File azzerati da disco pieno**: durante il blocco da disco pieno, alcuni file scritti erano rimasti a `\0` su disco (dimensione giusta) mentre il contenuto vero era solo in cache Windows → `docker build` li leggeva come zeri. Risolto riscrivendoli con flush. Se ricapita: rileggere dalla cache e riscrivere.
- **MissingGreenlet (SQLAlchemy async)**: dopo un UPDATE, i campi con `onupdate=func.now()` (es. `updated_at`) vengono scaduti; se Pydantic li legge in `model_validate` fuori dal contesto async → 500. **Fix**: `await db.refresh(obj)` dopo il `flush()`, prima di serializzare.
- **`docker-compose.override.yml` gitignored** ma necessario in locale (porte + `KEYCLOAK_URL=http://keycloak:8080` per il backend + `KC_HOSTNAME_PORT/PROXY` per keycloak). Una nuova macchina deve ricrearlo.
- **Chiave minter Amoy esposta in chat** (sessioni precedenti) → **ruotare prima del mainnet**.
- **Privilege escalation staff→dirigenza**: `modules/dirigenza/router.py` ha un `_require_dirigenza` che ammette anche `staff` (mentre `RequireDirigenza` è stretto). Da uniformare se non voluto.
- **Leak PII pubblico** su `/tessere/{id}/verifica` e `/pdf` (nome+cognome, anche minori) — **GDPR, da mitigare**.
- **N+1 residuo** su `/calendario/disponibilita` (prezzo per-slot in loop, scoped al mese).

# SICUREZZA (invariato, sintesi)

- Keycloak OIDC, JWT RS256 via `PyJWKClient`. Il backend valida firma + audience (`[millennio-backend, millennio-frontend, account]`) ma **non** l'issuer.
- Segreti in `.env` (root + `asd-millennio-backend/.env` + `contracts/.env`), **gitignored**; solo `.env.example` in git. Wallet custodiali AES-256-GCM. Stripe hosted (mai dati carta lato server), prezzo server-side, doppia verifica + refund idempotente.

# DECISION LOG (aggiunte di questa sessione)

Oltre a quelle P0–P3 precedenti (anti double-sell 2 livelli, coda mint conc.1, scarsità per-mese, token unico per contratto, mint firmato dal minter, dispatch post-commit, recupero orfano):
8. **Prenotazione campi per-ora senza migrazione di colonne**: `prenotazioni_campo` aveva già `ora_inizio/ora_fine/campo`; il lock `with_for_update` sul template serializza l'assegnazione → niente race, niente nuove colonne.
9. **Carrello con `stripe_session_id` condiviso**: più prenotazioni → una sessione Stripe (1 pagamento). Ha richiesto di **rimuovere il vincolo UNIQUE** su quella colonna (migration `20260705_120000`). L'idempotenza del webhook resta garantita da `webhook_log`.
10. **Auto-annullo via lock 30 min** (non via beacon on-unload): robusto lato server, non dipende dal browser.
11. **Chrome dirigenza nel `layout.tsx`** (non duplicata nelle pagine): tutte le pagine `/dirigenza` ereditano header+sidebar e il gate auth.
12. **Socio sostenitore → il pagante, mai il minore**: per acquisti `acquisto_per_minore`, la tessera SOS va sempre al socio che paga (`acquisto.socio_id`), non al minore beneficiario del diritto d'uso. Decisione utente esplicita (2026-07-09).

# TEST STATUS

- **Backend**: pytest mock-based; NFT/calendario verdi (non rieseguiti in questa sessione). Il **flusso carrello** è stato verificato eseguendo i service reali contro il DB (prenota×2 → carrello → disponibilità aggiornata → rimuovi → checkout Stripe reale €120/4slot → conferma multipla → cancella). `pytest` non è nell'immagine runtime (dev-dep).
- **Contratto**: 52/52 Hardhat, coverage ~97% stmts / 100% branch (dalla sessione precedente; rename verificato con `hardhat compile` OK).
- **Mancano**: integration webhook Stripe con DB, e2e frontend, test prenotazione campi automatizzati, checkout reale con carta di test via browser.

# NEXT STEPS (priorità)

1. **Aprire la PR** `fix/p0-payment-mint` → `main` (branch pushato, 11 commit avanti; `gh` non installato → form pre-compilato: https://github.com/romanobenit/Portale_Millennio/compare/main...fix/p0-payment-mint?expand=1).
2. **Configurare le quote** dalla dashboard dirigenza (`/dirigenza/quote`) — senza, l'auto-tesseramento si blocca.
3. **Configurare `RESEND_API_KEY`** (root `.env` + `asd-millennio-backend/.env`): oggi **vuota** → email certificato/tesseramento no-op (PDF resta scaricabile). Estendere Resend a refund/scadenze/notifiche verifica.
4. **Ruotare** la chiave minter Amoy (esposta in dev).
5. **Decidere** privilege escalation staff→dirigenza; **mitigare** leak PII pubblico su `/tessere/{id}/verifica` e `/pdf` (GDPR).
6. **UAT** end-to-end via browser (onboarding adulto + minore con checkout Stripe reale; verifica staff; auto-conferma) + DPIA (M01 tratta ora documenti d'identità!) + audit contratto pre-mainnet.
7. **Test** automatici integration (webhook Stripe tessera+nft con DB) + e2e frontend.
8. **Backup del volume `documenti_data`** (documenti sensibili) nella strategia di backup Hetzner.

# CRITICAL CONTEXT (per una nuova sessione)

1. Leggi `CLAUDE.md` (intero), `MEMORY.md` + i file di memoria, e questo handoff. Verifica `git status` (dovrebbe essere pulito; ultimo commit `f36d036` pushato su `fix/p0-payment-mint`), `alembic current` (`20260711_140000`), e che le immagini siano ricostruite con l'ultimo codice.
2. **Non fidarti che container/DB siano allineati al codice**: dopo modifiche serve `docker compose build <svc>` + `up -d`. Un `up -d` ricrea dall'immagine e annulla i `docker cp`.
3. **Contratto Amoy**: `CONTRACT_ADDRESS_PALASIRIO_NFT` nel `.env` root; contratto `PalasirioNFT` (rinominato). Per modifiche al contratto mostra il **diff** e chiedi approvazione (CLAUDE.md §10.5).
4. **PowerShell** come shell principale; evita here-string `@'...'@` (guard del sandbox) e redirezioni di stderr di comandi nativi.
5. **Memoria persistente** in `C:\Users\Romano\.claude\projects\F--millennio-flussocrazia\memory\`: `env_docker_disk.md`, `deploy_frontend_keycloak.md`, `project_review_state.md`, `user_profile.md`, `feedback_style.md`.

*Fine handoff — 2026-07-12.*
