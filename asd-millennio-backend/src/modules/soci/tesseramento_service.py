"""
Tesseramento self-service (onboarding). Flusso ibrido:
  onboarding + upload documento + paga quota → tessera ATTIVA in via provvisoria
  (verifica_stato='in_verifica', scadenza +N giorni) → staff conferma / silenzio-assenso.

Questo modulo copre l'onboarding dell'ADULTO (Fase 2). I minori (Fase 3) e la
verifica staff (Fase 4) si appoggiano agli stessi modelli.
"""
import asyncio
import time as time_module
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import stripe
from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from core import storage
from models.consenso import Consenso
from models.documento_socio import DocumentoSocio
from models.pagamento_tessera import PagamentoTessera
from models.quota_tessera import QuotaTessera
from models.socio import Socio
from models.tessera import Tessera
from models.tessera_esterna import TesseraEsterna
from modules.soci.codice_fiscale import cf_valido
from modules.soci.repository import SociRepository
from modules.soci.service import _calcola_scadenza_tessera, _genera_numero_tessera
from schemas.soci import SocioResponse
from schemas.tesseramento import DocumentoResponse, TesseramentoCheckoutResponse

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

# Consensi obbligatori prima del pagamento (CLAUDE.md §RF-M01-003)
CONSENSI_ADULTO = {"privacy", "trattamento_dati"}
# Minore: doppio consenso — privacy/trattamento firmati dal tutore + autorizzazione attività
CONSENSI_MINORE = {"privacy", "trattamento_dati", "foto_video"}


class TesseramentoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SociRepository(db)

    # ── profilo ───────────────────────────────────────────────────────────────

    async def crea_profilo_self(
        self, kc_sub: str, email: str | None, data, *, email_verified: bool = False,
    ) -> SocioResponse:
        """
        Crea il profilo dell'adulto al primo accesso, legato all'account Keycloak.
        Un solo profilo per account; se lo staff aveva già creato il socio con la
        stessa email, lo collega invece di duplicarlo — ma SOLO se l'email del
        token Keycloak è verificata. Senza questo controllo, chiunque conosca
        l'email di un socio già censito (es. da un'importazione CSV) potrebbe
        registrarsi con quella email e impossessarsi del suo profilo — tessere,
        CF e anagrafica comprese, dato che qui sotto li sovrascriviamo.
        """
        if await self.repo.get_by_keycloak_id(kc_sub):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Profilo già esistente per questo account")

        if not email:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email mancante nel profilo di accesso: impossibile creare il socio.",
            )

        if not cf_valido(data.codice_fiscale):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Codice fiscale non valido (carattere di controllo errato).",
            )

        # è un adulto: la data di nascita deve indicare la maggiore età
        if _eta(data.data_nascita) < 18:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Chi si registra deve essere maggiorenne. I minori vanno aggiunti dal tutore.",
            )

        # se lo staff aveva pre-creato il socio con questa email → collega e aggiorna
        esistente = await self.repo.get_by_email(email) if email else None
        if esistente and not esistente.keycloak_user_id:
            if not email_verified:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail=(
                        "Esiste già un profilo associato a questa email, ma il tuo indirizzo "
                        "non risulta verificato. Verifica l'email nel tuo account oppure "
                        "contatta l'associazione per collegare il profilo esistente."
                    ),
                )
            esistente.keycloak_user_id = kc_sub
            esistente.nome = data.nome
            esistente.cognome = data.cognome
            esistente.data_nascita = data.data_nascita
            esistente.codice_fiscale = data.codice_fiscale
            esistente.indirizzo = data.indirizzo
            esistente.telefono = data.telefono
            await self.db.flush()
            await self.db.refresh(esistente)
            return SocioResponse.model_validate(esistente)

        if await self.repo.get_by_cf(data.codice_fiscale):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Codice fiscale già registrato")
        if email and await self.repo.get_by_email(email):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email già registrata")

        socio = Socio(
            nome=data.nome,
            cognome=data.cognome,
            data_nascita=data.data_nascita,
            codice_fiscale=data.codice_fiscale,
            email=email,
            indirizzo=data.indirizzo,
            telefono=data.telefono,
            is_minor=False,
            keycloak_user_id=kc_sub,
            sport=[],
        )
        self.db.add(socio)
        await self.db.flush()
        await self.db.refresh(socio)
        return SocioResponse.model_validate(socio)

    async def crea_minore(self, tutore: Socio, data) -> SocioResponse:
        """
        Il tutore aggiunge un figlio minorenne. Il minore NON ha login proprio:
        è gestito dal tutore. Email sintetica (nessun account, nessuna PII derivata dal CF).
        """
        if not cf_valido(data.codice_fiscale):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Codice fiscale del minore non valido.",
            )
        if _eta(data.data_nascita) >= 18:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La persona indicata non è minorenne.",
            )
        if await self.repo.get_by_cf(data.codice_fiscale):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Codice fiscale già registrato")

        from uuid import uuid4
        minore = Socio(
            nome=data.nome,
            cognome=data.cognome,
            data_nascita=data.data_nascita,
            codice_fiscale=data.codice_fiscale,
            # nessun account: email sintetica univoca (i minori non fanno login)
            email=f"minore-{uuid4().hex}@minori.millennioasd.local",
            indirizzo=data.indirizzo,
            is_minor=True,
            tutore_id=tutore.id,
            keycloak_user_id=None,
            sport=[],
        )
        self.db.add(minore)
        await self.db.flush()
        await self.db.refresh(minore)
        return SocioResponse.model_validate(minore)

    # ── documenti ─────────────────────────────────────────────────────────────

    async def carica_documento(
        self, socio_id: UUID, caricato_da: UUID, tipo: str,
        filename: str, content_type: str, content: bytes,
    ) -> DocumentoResponse:
        if tipo not in ("identita", "tutela"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tipo documento non valido")
        try:
            rel_path, size = storage.salva_documento(content, content_type)
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        doc = DocumentoSocio(
            socio_id=socio_id,
            tipo=tipo,
            filename=filename[:255],
            content_type=content_type,
            storage_path=rel_path,
            size_bytes=size,
            caricato_da=caricato_da,
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return DocumentoResponse.model_validate(doc)

    async def lista_documenti(self, socio_id: UUID) -> list[DocumentoResponse]:
        result = await self.db.execute(
            select(DocumentoSocio)
            .where(DocumentoSocio.socio_id == socio_id)
            .order_by(DocumentoSocio.created_at.desc())
        )
        return [DocumentoResponse.model_validate(d) for d in result.scalars().all()]

    async def carica_certificato_medico(
        self, tessera: Tessera, caricato_da: UUID, tipo: str, scadenza: date,
        filename: str, content_type: str, content: bytes,
    ):
        """
        Certificato di idoneità sportiva (non agonistico/agonistico), self-service.
        Informativo: non cambia lo stato della tessera, solo tracciato per la dirigenza.
        """
        from schemas.tessere import TesseraResponse

        if tipo not in ("non_agonistico", "agonistico"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tipo certificato non valido")
        try:
            rel_path, size = storage.salva_documento(content, content_type)
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        doc = DocumentoSocio(
            socio_id=tessera.socio_id,
            tipo="certificato_medico",
            filename=filename[:255],
            content_type=content_type,
            storage_path=rel_path,
            size_bytes=size,
            caricato_da=caricato_da,
        )
        self.db.add(doc)
        tessera.certificato_medico_tipo = tipo
        tessera.certificato_medico_scadenza = scadenza
        await self.db.flush()
        await self.db.refresh(tessera)
        return TesseraResponse.model_validate(tessera)

    # ── tessera di un'altra ASD (iscrizione community) ─────────────────────────

    async def carica_tessera_esterna(
        self, socio_id: UUID, caricato_da: UUID, dati,
        filename: str, content_type: str, content: bytes,
    ):
        from schemas.tesseramento import TesseraEsternaResponse

        if dati.data_scadenza < date.today():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La tessera risulta già scaduta: carica quella in corso di validità.",
            )
        try:
            rel_path, size = storage.salva_documento(content, content_type)
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        doc = DocumentoSocio(
            socio_id=socio_id, tipo="tessera_esterna", filename=filename[:255],
            content_type=content_type, storage_path=rel_path, size_bytes=size, caricato_da=caricato_da,
        )
        self.db.add(doc)
        await self.db.flush()
        te = TesseraEsterna(
            socio_id=socio_id,
            ente=dati.ente,
            asd_nome=dati.asd_nome,
            asd_codice=dati.asd_codice or None,
            numero_tessera=dati.numero_tessera,
            disciplina=dati.disciplina,
            data_scadenza=dati.data_scadenza,
            documento_id=doc.id,
            verifica_stato="in_verifica",
            verifica_scadenza=datetime.now(timezone.utc) + timedelta(days=settings.tesseramento_verifica_giorni),
            caricata_da=caricato_da,
        )
        self.db.add(te)
        await self.db.flush()
        await self.db.refresh(te)
        logger.info("Tessera esterna caricata: %s (socio %s)", te.id, socio_id)
        return TesseraEsternaResponse.model_validate(te)

    async def lista_tessere_esterne(self, socio_id: UUID) -> list:
        from schemas.tesseramento import TesseraEsternaResponse

        r = await self.db.execute(
            select(TesseraEsterna).where(TesseraEsterna.socio_id == socio_id)
            .order_by(TesseraEsterna.created_at.desc())
        )
        return [TesseraEsternaResponse.model_validate(t) for t in r.scalars().all()]

    async def _tessera_esterna_valida(self, socio_id: UUID) -> TesseraEsterna | None:
        return (await self.db.execute(
            select(TesseraEsterna).where(
                TesseraEsterna.socio_id == socio_id,
                TesseraEsterna.verifica_stato != "rifiutata",
                TesseraEsterna.data_scadenza >= date.today(),
            ).order_by(TesseraEsterna.created_at.desc())
        )).scalars().first()

    async def _ultima_tessera_esterna_in_verifica(self, socio_id: UUID) -> TesseraEsterna | None:
        return (await self.db.execute(
            select(TesseraEsterna).where(
                TesseraEsterna.socio_id == socio_id, TesseraEsterna.verifica_stato == "in_verifica",
            ).order_by(TesseraEsterna.created_at.desc())
        )).scalars().first()

    async def _ha_documento(self, socio_id: UUID, tipo: str) -> bool:
        r = await self.db.execute(
            select(DocumentoSocio).where(
                DocumentoSocio.socio_id == socio_id, DocumentoSocio.tipo == tipo
            )
        )
        return r.scalars().first() is not None

    async def _consensi_ok(self, socio_id: UUID, richiesti: set[str]) -> bool:
        r = await self.db.execute(
            select(Consenso.tipo).where(
                Consenso.socio_id == socio_id, Consenso.revocato_at.is_(None)
            )
        )
        presenti = {row[0] for row in r.all()}
        return richiesti.issubset(presenti)

    # ── tesseramento + pagamento quota ────────────────────────────────────────

    async def _quota(self, categoria: str, is_minore: bool, anno: str) -> QuotaTessera:
        r = await self.db.execute(
            select(QuotaTessera).where(
                QuotaTessera.categoria == categoria,
                QuotaTessera.is_minore == is_minore,
                QuotaTessera.anno_sportivo == anno,
                QuotaTessera.attivo.is_(True),
            )
        )
        quota = r.scalars().first()
        if not quota:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Quota non configurata per questa categoria. Contatta l'associazione.",
            )
        return quota

    async def avvia_tesseramento(
        self, socio: Socio, categoria: str, is_minore: bool = False,
        pagante_socio_id: UUID | None = None,
    ) -> TesseramentoCheckoutResponse:
        """
        Crea la tessera in attesa di pagamento + la sessione Stripe della quota.
        Valida che ci siano documento d'identità e consensi prima di far pagare.
        `pagante_socio_id` = chi paga (il tutore per i minori; il socio stesso altrimenti).
        """
        pagante = pagante_socio_id or socio.id
        anno = settings.anno_sportivo_corrente

        if not await self._ha_documento(socio.id, "identita"):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Carica il documento d'identità prima di procedere al pagamento.",
            )
        if is_minore:
            if not await self._ha_documento(socio.id, "tutela"):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Carica il documento che prova la tutela del minore prima di procedere.",
                )
            if not await self._consensi_ok(socio.id, CONSENSI_MINORE):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Firma il doppio consenso del minore (privacy, trattamento dati, foto/video).",
                )
        else:
            if not await self._consensi_ok(socio.id, CONSENSI_ADULTO):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Firma i consensi privacy e trattamento dati prima di procedere.",
                )

        community = categoria == "community"
        # niente doppioni: una tessera attiva/in attesa per (categoria, anno);
        # l'iscrizione community non scade, quindi una sola in assoluto.
        q_esistente = select(Tessera).where(
            Tessera.socio_id == socio.id,
            Tessera.sport == categoria,
            Tessera.stato.in_(["in_attesa_pagamento", "attiva"]),
        )
        if not community:
            q_esistente = q_esistente.where(Tessera.anno_sportivo == anno)
        if (await self.db.execute(q_esistente)).scalars().first():
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Iscrizione community già presente." if community
                else "Esiste già una tessera per questa categoria e anno sportivo.",
            )
        if community and not await self._tessera_esterna_valida(socio.id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Carica la tessera della tua ASD (in corso di validità) prima di procedere.",
            )

        quota = await self._quota(categoria, is_minore, anno)

        numero = await _genera_numero_tessera(self.db, categoria, anno)
        tessera = Tessera(
            socio_id=socio.id,
            numero_tessera=numero,
            sport=categoria,
            stato="in_attesa_pagamento",
            anno_sportivo=anno,
            data_scadenza=None if community else _calcola_scadenza_tessera(anno),
            data_emissione=date.today(),
        )
        self.db.add(tessera)
        try:
            await self.db.flush()
        except IntegrityError:
            # Rete di sicurezza contro il TOCTOU del controllo "esistente" sopra:
            # due richieste concorrenti (doppio click, due tab) possono superarlo
            # entrambe. L'indice parziale uq_tessere_socio_sport_anno_attiva
            # (migration 20260919_120000) fa rispettare la regola a livello DB.
            await self.db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Esiste già una tessera per questa categoria e anno sportivo.",
            )

        pagamento = PagamentoTessera(
            tessera_id=tessera.id,
            pagante_socio_id=pagante,
            stripe_session_id="",
            importo_eur=quota.importo_eur,
            stato="in_attesa_pagamento",
        )
        self.db.add(pagamento)
        await self.db.flush()

        stripe_session = await self._crea_sessione_stripe_quota(pagamento, categoria)
        pagamento.stripe_session_id = stripe_session.id
        await self.db.flush()

        return TesseramentoCheckoutResponse(
            tessera_id=tessera.id,
            pagamento_id=pagamento.id,
            stripe_checkout_url=stripe_session.url,
            importo_eur=float(quota.importo_eur),
        )

    async def _crea_sessione_stripe_quota(self, pagamento: PagamentoTessera, categoria: str):
        """Crea una sessione Stripe Checkout per il pagamento (nuovo o da riprendere) della quota."""
        unit_amount = int(round(float(pagamento.importo_eur) * 100))
        return await asyncio.to_thread(
            stripe.checkout.Session.create,
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": unit_amount,
                    "product_data": {"name": "Iscrizione community ASD Millennio" if categoria == "community"
                                     else f"Quota associativa ASD Millennio — {categoria}"},
                },
                "quantity": 1,
            }],
            mode="payment",
            expires_at=int(time_module.time()) + 24 * 3600,
            success_url=f"{settings.app_url}/dashboard/tessere?tesseramento=success",
            cancel_url=f"{settings.app_url}/dashboard/tessere?tesseramento=cancel",
            metadata={"tipo": "tessera", "pagamento_tessera_id": str(pagamento.id)},
            payment_intent_data={"metadata": {"pagamento_tessera_id": str(pagamento.id)}},
        )

    async def riprendi_pagamento(self, tessera_id: UUID, socio_id: UUID) -> TesseramentoCheckoutResponse:
        """
        Recupera (o ricrea se scaduta) la sessione Stripe di una tessera già in
        attesa di pagamento — per completare un tesseramento avviato in
        precedenza e mai portato a termine. Riusa la sessione esistente se
        ancora aperta, invece di generarne una nuova ad ogni click.
        """
        tessera = (await self.db.execute(
            select(Tessera).where(Tessera.id == tessera_id, Tessera.socio_id == socio_id)
        )).scalar_one_or_none()
        if not tessera or tessera.stato != "in_attesa_pagamento":
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Nessun pagamento in sospeso per questa tessera.",
            )

        pagamento = (await self.db.execute(
            select(PagamentoTessera).where(
                PagamentoTessera.tessera_id == tessera.id,
                PagamentoTessera.stato == "in_attesa_pagamento",
            )
        )).scalars().first()
        if not pagamento:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Nessun pagamento in sospeso per questa tessera.",
            )

        session = None
        if pagamento.stripe_session_id:
            try:
                session = await asyncio.to_thread(
                    stripe.checkout.Session.retrieve, pagamento.stripe_session_id
                )
            except stripe.error.InvalidRequestError:
                session = None  # sessione non più trovabile su Stripe: ne creiamo una nuova

        if session and session.status == "complete":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Il pagamento risulta già completato: aggiorna la pagina tra qualche secondo.",
            )

        if not session or session.status != "open":
            session = await self._crea_sessione_stripe_quota(pagamento, tessera.sport)
            pagamento.stripe_session_id = session.id
            await self.db.flush()

        return TesseramentoCheckoutResponse(
            tessera_id=tessera.id,
            pagamento_id=pagamento.id,
            stripe_checkout_url=session.url,
            importo_eur=float(pagamento.importo_eur),
        )

    async def conferma_pagamento_tessera(self, stripe_session_id: str) -> None:
        """
        Webhook checkout.session.completed (tipo=tessera): la quota è pagata →
        la tessera diventa ATTIVA in via provvisoria (verifica in corso, +N giorni).
        """
        pagamento = (await self.db.execute(
            select(PagamentoTessera).where(PagamentoTessera.stripe_session_id == stripe_session_id)
        )).scalar_one_or_none()
        if not pagamento or pagamento.stato != "in_attesa_pagamento":
            logger.info("Pagamento tessera già processato o assente: %s", stripe_session_id)
            return

        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, stripe_session_id)
        if session.payment_status != "paid":
            return

        pagamento.stripe_payment_id = session.payment_intent
        pagamento.stato = "pagato"

        tessera = (await self.db.execute(
            select(Tessera).where(Tessera.id == pagamento.tessera_id)
        )).scalar_one_or_none()
        if tessera:
            tessera.stato = "attiva"  # provvisoria
            tessera.verifica_stato = "in_verifica"
            tessera.verifica_scadenza = datetime.now(timezone.utc) + timedelta(
                days=settings.tesseramento_verifica_giorni
            )
            tessera.pdf_url = f"{settings.app_url}/api/v1/tessere/{tessera.id}/pdf"
        await self.db.flush()
        logger.info("Tessera %s attiva provvisoria (verifica entro %d gg).",
                    pagamento.tessera_id, settings.tesseramento_verifica_giorni)

    async def gestisci_pagamento_fallito(
        self, *, stripe_session_id: str | None = None, pagamento_tessera_id: UUID | None = None,
    ) -> None:
        """
        Webhook checkout.session.expired / payment_intent.payment_failed (tipo=tessera).

        `avvia_tesseramento` crea la tessera e il pagamento PRIMA che l'utente paghi
        davvero (per poter creare la sessione Stripe): se il pagamento scade o
        fallisce, quel placeholder va rimosso, altrimenti il controllo anti-doppione
        in `avvia_tesseramento` blocca per sempre qualsiasi nuovo tentativo per la
        stessa categoria/anno sportivo (a differenza del flusso NFT, qui non c'è un
        endpoint staff per sbloccarlo manualmente).
        """
        if pagamento_tessera_id is not None:
            pagamento = (await self.db.execute(
                select(PagamentoTessera).where(PagamentoTessera.id == pagamento_tessera_id)
            )).scalar_one_or_none()
        elif stripe_session_id is not None:
            pagamento = (await self.db.execute(
                select(PagamentoTessera).where(PagamentoTessera.stripe_session_id == stripe_session_id)
            )).scalar_one_or_none()
        else:
            return

        if not pagamento or pagamento.stato != "in_attesa_pagamento":
            return  # già pagato, già ripulito, o mai esistito: idempotente

        tessera = (await self.db.execute(
            select(Tessera).where(Tessera.id == pagamento.tessera_id)
        )).scalar_one_or_none()

        await self.db.delete(pagamento)
        if tessera and tessera.stato == "in_attesa_pagamento":
            await self.db.delete(tessera)
        await self.db.flush()
        logger.info(
            "Tesseramento abbandonato/fallito: rimossa tessera placeholder %s (pagamento %s).",
            tessera.id if tessera else "?", pagamento.id,
        )

    # ── verifica staff ────────────────────────────────────────────────────────

    async def lista_da_verificare(self) -> list:
        from schemas.tesseramento import (
            DocumentoBreve, SocioBreve, TesseramentoDaVerificare,
        )

        from schemas.tesseramento import TesseraEsternaResponse

        tessere = (await self.db.execute(
            select(Tessera).where(Tessera.verifica_stato == "in_verifica")
            .order_by(Tessera.verifica_scadenza)
        )).scalars().all()

        out = []
        for t in tessere:
            socio = await self.repo.get_by_id(t.socio_id)
            if not socio:
                continue
            tutore = await self.repo.get_by_id(socio.tutore_id) if socio.tutore_id else None
            docs = (await self.db.execute(
                select(DocumentoSocio).where(DocumentoSocio.socio_id == t.socio_id)
            )).scalars().all()
            pag = (await self.db.execute(
                select(PagamentoTessera).where(PagamentoTessera.tessera_id == t.id)
            )).scalars().first()
            te = await self._ultima_tessera_esterna_in_verifica(t.socio_id) if t.sport == "community" else None
            out.append(TesseramentoDaVerificare(
                tessera_id=t.id,
                numero_tessera=t.numero_tessera,
                categoria=t.sport,
                anno_sportivo=t.anno_sportivo,
                verifica_scadenza=t.verifica_scadenza,
                importo_eur=float(pag.importo_eur) if pag else None,
                socio=self._breve(socio),
                tutore=self._breve(tutore) if tutore else None,
                documenti=[DocumentoBreve(id=d.id, tipo=d.tipo, filename=d.filename) for d in docs],
                tessera_esterna=TesseraEsternaResponse.model_validate(te) if te else None,
            ))

        # Rinnovi: tessera esterna aggiornata da chi ha già un'iscrizione community verificata.
        rinnovi = (await self.db.execute(
            select(TesseraEsterna, Tessera)
            .join(Tessera, and_(
                Tessera.socio_id == TesseraEsterna.socio_id,
                Tessera.sport == "community",
                Tessera.stato == "attiva",
            ))
            .where(
                TesseraEsterna.verifica_stato == "in_verifica",
                or_(Tessera.verifica_stato.is_(None), Tessera.verifica_stato != "in_verifica"),
            )
            .order_by(TesseraEsterna.verifica_scadenza)
        )).all()
        for te, t in rinnovi:
            socio = await self.repo.get_by_id(te.socio_id)
            if not socio:
                continue
            tutore = await self.repo.get_by_id(socio.tutore_id) if socio.tutore_id else None
            doc = (await self.db.execute(
                select(DocumentoSocio).where(DocumentoSocio.id == te.documento_id)
            )).scalar_one_or_none() if te.documento_id else None
            out.append(TesseramentoDaVerificare(
                tipo="rinnovo_tessera_esterna",
                tessera_id=t.id,
                numero_tessera=t.numero_tessera,
                categoria=t.sport,
                anno_sportivo=t.anno_sportivo,
                verifica_scadenza=te.verifica_scadenza,
                importo_eur=None,
                socio=self._breve(socio),
                tutore=self._breve(tutore) if tutore else None,
                documenti=[DocumentoBreve(id=doc.id, tipo=doc.tipo, filename=doc.filename)] if doc else [],
                tessera_esterna=TesseraEsternaResponse.model_validate(te),
            ))
        return out

    @staticmethod
    def _breve(s: Socio):
        from schemas.tesseramento import SocioBreve
        return SocioBreve(
            id=s.id, nome=s.nome, cognome=s.cognome, codice_fiscale=s.codice_fiscale, is_minor=s.is_minor,
        )

    async def lista_tesserati(
        self, stato: str | None = None, categoria: str | None = None, anno_sportivo: str | None = None,
    ) -> list:
        """Elenco completo dei tesserati (tutte le tessere, non solo quelle in verifica), con filtri opzionali."""
        from sqlalchemy.orm import aliased
        from schemas.tesseramento import SocioBreve, TesseratoResponse

        Tutore = aliased(Socio)
        q = (
            select(Tessera, Socio, Tutore)
            .join(Socio, Tessera.socio_id == Socio.id)
            .outerjoin(Tutore, Socio.tutore_id == Tutore.id)
        )
        if stato:
            q = q.where(Tessera.stato == stato)
        if categoria:
            q = q.where(Tessera.sport == categoria)
        if anno_sportivo:
            q = q.where(Tessera.anno_sportivo == anno_sportivo)
        q = q.order_by(Socio.cognome, Socio.nome)

        rows = (await self.db.execute(q)).all()
        scad_esterne = dict((await self.db.execute(
            select(TesseraEsterna.socio_id, func.max(TesseraEsterna.data_scadenza))
            .where(TesseraEsterna.verifica_stato != "rifiutata")
            .group_by(TesseraEsterna.socio_id)
        )).all())
        return [
            TesseratoResponse(
                tessera_esterna_scadenza=scad_esterne.get(socio.id) if t.sport == "community" else None,
                tessera_id=t.id,
                numero_tessera=t.numero_tessera,
                categoria=t.sport,
                stato=t.stato,
                anno_sportivo=t.anno_sportivo,
                data_scadenza=t.data_scadenza,
                verifica_stato=t.verifica_stato,
                certificato_medico_tipo=t.certificato_medico_tipo,
                certificato_medico_scadenza=t.certificato_medico_scadenza,
                socio=SocioBreve(
                    id=socio.id, nome=socio.nome, cognome=socio.cognome,
                    codice_fiscale=socio.codice_fiscale, is_minor=socio.is_minor,
                ),
                tutore=SocioBreve(
                    id=tutore.id, nome=tutore.nome, cognome=tutore.cognome,
                    codice_fiscale=tutore.codice_fiscale, is_minor=tutore.is_minor,
                ) if tutore else None,
            )
            for t, socio, tutore in rows
        ]

    async def _get_tessera_in_verifica(self, tessera_id: UUID) -> Tessera:
        t = (await self.db.execute(
            select(Tessera).where(Tessera.id == tessera_id)
        )).scalar_one_or_none()
        if not t:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tessera non trovata")
        if t.verifica_stato != "in_verifica":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Tesseramento non in verifica")
        return t

    async def conferma_verifica(self, tessera_id: UUID, verificatore_socio_id: UUID | None) -> None:
        t = await self._get_tessera_in_verifica(tessera_id)
        t.verifica_stato = "confermata"
        t.verificata_da = verificatore_socio_id
        t.verificata_at = datetime.now(timezone.utc)
        if t.sport == "community":
            await self._esito_tessera_esterna_iniziale(t.socio_id, "confermata", verificatore_socio_id)
        await self.db.flush()
        logger.info("Tesseramento %s confermato dallo staff.", tessera_id)

    async def _esito_tessera_esterna_iniziale(self, socio_id: UUID, esito: str, verificatore: UUID | None) -> None:
        """La tessera esterna caricata con l'iscrizione community segue l'esito dell'iscrizione."""
        te = await self._ultima_tessera_esterna_in_verifica(socio_id)
        if te:
            te.verifica_stato = esito
            te.verificata_da = verificatore
            te.verificata_at = datetime.now(timezone.utc)

    async def esito_tessera_esterna(self, tessera_esterna_id: UUID, esito: str, verificatore: UUID | None) -> None:
        """Verifica di una tessera esterna aggiornata (rinnovo): nessun effetto sui pagamenti."""
        te = (await self.db.execute(
            select(TesseraEsterna).where(TesseraEsterna.id == tessera_esterna_id)
        )).scalar_one_or_none()
        if not te:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tessera esterna non trovata")
        if te.verifica_stato != "in_verifica":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Tessera esterna non in verifica")
        te.verifica_stato = esito
        te.verificata_da = verificatore
        te.verificata_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("Tessera esterna %s → %s", tessera_esterna_id, esito)

    async def rifiuta_verifica(self, tessera_id: UUID, verificatore_socio_id: UUID | None) -> None:
        """
        Rifiuto: la tessera decade (sospesa) e la quota NON viene rimborsata ma
        riclassificata come erogazione liberale.
        """
        t = await self._get_tessera_in_verifica(tessera_id)
        t.verifica_stato = "rifiutata"
        t.stato = "sospesa"
        t.verificata_da = verificatore_socio_id
        t.verificata_at = datetime.now(timezone.utc)
        pag = (await self.db.execute(
            select(PagamentoTessera).where(PagamentoTessera.tessera_id == t.id)
        )).scalars().first()
        if pag and pag.stato == "pagato":
            pag.stato = "erogazione_liberale"
        if t.sport == "community":
            await self._esito_tessera_esterna_iniziale(t.socio_id, "rifiutata", verificatore_socio_id)
        await self.db.flush()
        logger.info("Tesseramento %s rifiutato → quota come erogazione liberale.", tessera_id)

    async def auto_conferma_scadute(self) -> int:
        """Silenzio-assenso: conferma i tesseramenti in verifica scaduti (30gg)."""
        now = datetime.now(timezone.utc)
        tessere = (await self.db.execute(
            select(Tessera).where(
                Tessera.verifica_stato == "in_verifica",
                Tessera.verifica_scadenza <= now,
            )
        )).scalars().all()
        for t in tessere:
            t.verifica_stato = "confermata"
            t.verificata_at = now  # verificata_da resta NULL = conferma automatica
        esterne = (await self.db.execute(
            select(TesseraEsterna).where(
                TesseraEsterna.verifica_stato == "in_verifica",
                TesseraEsterna.verifica_scadenza <= now,
            )
        )).scalars().all()
        for te in esterne:
            te.verifica_stato = "confermata"
            te.verificata_at = now
        if tessere or esterne:
            await self.db.flush()
        return len(tessere) + len(esterne)

    # ── tesseramento in sede (dirigenza/staff) ─────────────────────────────────

    async def tesseramento_in_sede(self, data, operatore_kc_sub: str):
        """
        Socio esistente o nuovo + tessera ATTIVA in una sola transazione: quota
        pagata in sede e documento visto di persona, quindi niente verifica a
        posteriori. Se la persona si registra poi al portale con la stessa email
        verificata, il profilo viene collegato in automatico (crea_profilo_self).
        """
        from schemas.tesseramento import TesseramentoInSedeResponse

        if not data.consensi_firmati:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Servono i consensi privacy e trattamento dati firmati sul modulo cartaceo.",
            )
        now = datetime.now(timezone.utc)

        if data.socio_id:
            socio = await self.repo.get_by_id(data.socio_id)
            if not socio:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")
            if socio.is_minor:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="I minori si tesserano dall'area soci del tutore.",
                )
        else:
            a = data.anagrafica
            if not cf_valido(a.codice_fiscale):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Codice fiscale non valido (carattere di controllo errato).",
                )
            if _eta(a.data_nascita) < 18:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Da qui si tesserano solo maggiorenni: i minori vanno aggiunti dal tutore.",
                )
            if await self.repo.get_by_cf(a.codice_fiscale):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Codice fiscale già registrato: cerca la persona tra i soci esistenti.",
                )
            if await self.repo.get_by_email(a.email):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Email già registrata: cerca la persona tra i soci esistenti.",
                )
            socio = Socio(
                nome=a.nome.strip(),
                cognome=a.cognome.strip(),
                data_nascita=a.data_nascita,
                codice_fiscale=a.codice_fiscale,
                email=a.email,
                telefono=a.telefono,
                indirizzo=a.indirizzo,
                is_minor=False,
                sport=[],
            )
            self.db.add(socio)
            await self.db.flush()

        anno = settings.anno_sportivo_corrente
        gia = (await self.db.execute(
            select(Tessera.id).where(
                Tessera.socio_id == socio.id,
                Tessera.sport == data.categoria,
                Tessera.anno_sportivo == anno,
                Tessera.stato.in_(["in_attesa_pagamento", "attiva"]),
            )
        )).scalars().first()
        if gia:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"{socio.nome} {socio.cognome} ha già una tessera {data.categoria} per il {anno}.",
            )

        operatore = await self.repo.get_by_keycloak_id(operatore_kc_sub)
        tessera = Tessera(
            socio_id=socio.id,
            numero_tessera=await _genera_numero_tessera(self.db, data.categoria, anno),
            sport=data.categoria,
            stato="attiva",
            anno_sportivo=anno,
            data_emissione=date.today(),
            data_scadenza=_calcola_scadenza_tessera(anno),
            verifica_stato="confermata",
            verificata_da=operatore.id if operatore else None,
            verificata_at=now,
        )
        self.db.add(tessera)
        try:
            await self.db.flush()
        except IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Tesseramento concorrente in corso: riprova.")
        tessera.pdf_url = f"{settings.app_url}/api/v1/tessere/{tessera.id}/pdf"

        attivi = set((await self.db.execute(
            select(Consenso.tipo).where(Consenso.socio_id == socio.id, Consenso.revocato_at.is_(None))
        )).scalars().all())
        for tipo in ("privacy", "trattamento_dati"):
            if tipo not in attivi:
                self.db.add(Consenso(
                    socio_id=socio.id, tipo=tipo, testo_versione="v1-cartaceo",
                    firmato_da=socio.id, timestamp_firma=now,
                ))
        await self.db.flush()
        logger.info("Tesseramento in sede: tessera %s emessa da operatore %s", tessera.id, operatore_kc_sub)
        return TesseramentoInSedeResponse(
            socio_id=socio.id, nome=socio.nome, cognome=socio.cognome,
            tessera_id=tessera.id, numero_tessera=tessera.numero_tessera,
            categoria=tessera.sport, data_scadenza=tessera.data_scadenza,
        )

    async def importa_in_sede(
        self, content: bytes, categoria: str, consensi_firmati: bool, conferma: bool, operatore_kc_sub: str,
    ):
        """
        Tesseramento in sede da file. Anteprima (conferma=False): ogni riga gira in un
        savepoint annullato, così l'esito mostrato è quello reale senza scrivere nulla.
        Importazione: le righe valide vengono salvate, quelle con errori saltate.
        """
        from pydantic import ValidationError
        from modules.soci.import_tesserati import leggi_file
        from schemas.tesseramento import (
            AnagraficaInSede, EsitoImportRiga, ImportTesseratiResponse, TesseramentoInSedeRequest,
        )

        try:
            righe = leggi_file(content)
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        if conferma and not consensi_firmati:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Conferma che consensi e quote sono stati raccolti in sede.",
            )

        esiti: list = []
        for r in righe:
            base = dict(riga=r.riga, cognome=r.valori.get("cognome", ""), nome=r.valori.get("nome", ""))
            if r.errore:
                esiti.append(EsitoImportRiga(**base, esito="errore", messaggio=r.errore))
                continue
            sp = await self.db.begin_nested()
            try:
                esistente = await self.repo.get_by_cf(r.valori["codice_fiscale"])
                tipo = "esistente" if esistente else "nuovo"
                if esistente:
                    req = TesseramentoInSedeRequest(socio_id=esistente.id, categoria=categoria, consensi_firmati=True)
                else:
                    req = TesseramentoInSedeRequest(
                        anagrafica=AnagraficaInSede(**{
                            k: r.valori.get(k)
                            for k in ("nome", "cognome", "data_nascita", "codice_fiscale", "email", "telefono", "indirizzo")
                        }),
                        categoria=categoria,
                        consensi_firmati=True,
                    )
                esito = await self.tesseramento_in_sede(req, operatore_kc_sub)
                if conferma:
                    await sp.commit()
                else:
                    await sp.rollback()
                esiti.append(EsitoImportRiga(
                    **base, esito=tipo,
                    numero_tessera=esito.numero_tessera if conferma else None,
                    messaggio="socio già registrato: aggiunta la tessera" if tipo == "esistente" else None,
                ))
            except HTTPException as e:
                await sp.rollback()
                esiti.append(EsitoImportRiga(**base, esito="errore", messaggio=str(e.detail)))
            except ValidationError as e:
                await sp.rollback()
                campi = {str(err["loc"][-1]) for err in e.errors() if err.get("loc")}
                esiti.append(EsitoImportRiga(
                    **base, esito="errore",
                    messaggio="email non valida" if "email" in campi else "dati non validi",
                ))

        if conferma:
            await self.db.flush()
            logger.info("Import tesserati in sede: %d righe, operatore %s", len(esiti), operatore_kc_sub)
        return ImportTesseratiResponse(
            importato=conferma,
            righe=esiti,
            nuovi=sum(e.esito == "nuovo" for e in esiti),
            esistenti=sum(e.esito == "esistente" for e in esiti),
            errori=sum(e.esito == "errore" for e in esiti),
        )

    # ── quote (dirigenza) ──────────────────────────────────────────────────────

    async def lista_quote(self, anno_sportivo: str | None = None) -> list[QuotaTessera]:
        q = select(QuotaTessera)
        if anno_sportivo:
            q = q.where(QuotaTessera.anno_sportivo == anno_sportivo)
        r = await self.db.execute(q.order_by(QuotaTessera.categoria, QuotaTessera.is_minore))
        return list(r.scalars().all())

    async def crea_quota(self, data) -> QuotaTessera:
        esiste = (await self.db.execute(
            select(QuotaTessera).where(
                QuotaTessera.categoria == data.categoria,
                QuotaTessera.is_minore == data.is_minore,
                QuotaTessera.anno_sportivo == data.anno_sportivo,
            )
        )).scalars().first()
        if esiste:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Quota già presente per categoria/minore/anno.",
            )
        quota = QuotaTessera(
            categoria=data.categoria, is_minore=data.is_minore,
            importo_eur=data.importo_eur, anno_sportivo=data.anno_sportivo,
            note=data.note, attivo=True,
        )
        self.db.add(quota)
        await self.db.flush()
        await self.db.refresh(quota)
        return quota

    async def aggiorna_quota(self, quota_id: UUID, data) -> QuotaTessera:
        quota = (await self.db.execute(
            select(QuotaTessera).where(QuotaTessera.id == quota_id)
        )).scalar_one_or_none()
        if not quota:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quota non trovata")
        if data.importo_eur is not None:
            quota.importo_eur = data.importo_eur
        if data.attivo is not None:
            quota.attivo = data.attivo
        if data.note is not None:
            quota.note = data.note
        await self.db.flush()
        await self.db.refresh(quota)
        return quota


def _eta(nascita: date) -> int:
    oggi = date.today()
    return oggi.year - nascita.year - ((oggi.month, oggi.day) < (nascita.month, nascita.day))
