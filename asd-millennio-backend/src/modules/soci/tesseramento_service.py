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
from sqlalchemy import select
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

    async def crea_profilo_self(self, kc_sub: str, email: str | None, data) -> SocioResponse:
        """
        Crea il profilo dell'adulto al primo accesso, legato all'account Keycloak.
        Un solo profilo per account; se lo staff aveva già creato il socio con la
        stessa email, lo collega invece di duplicarlo.
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

        # niente doppioni: una tessera attiva/in attesa per (categoria, anno)
        esistente = (await self.db.execute(
            select(Tessera).where(
                Tessera.socio_id == socio.id,
                Tessera.sport == categoria,
                Tessera.anno_sportivo == anno,
                Tessera.stato.in_(["in_attesa_pagamento", "attiva"]),
            )
        )).scalars().first()
        if esistente:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Esiste già una tessera per questa categoria e anno sportivo.",
            )

        quota = await self._quota(categoria, is_minore, anno)

        numero = await _genera_numero_tessera(self.db, categoria, anno)
        tessera = Tessera(
            socio_id=socio.id,
            numero_tessera=numero,
            sport=categoria,
            stato="in_attesa_pagamento",
            anno_sportivo=anno,
            data_scadenza=_calcola_scadenza_tessera(anno),
            data_emissione=date.today(),
        )
        self.db.add(tessera)
        await self.db.flush()

        pagamento = PagamentoTessera(
            tessera_id=tessera.id,
            pagante_socio_id=pagante,
            stripe_session_id="",
            importo_eur=quota.importo_eur,
            stato="in_attesa_pagamento",
        )
        self.db.add(pagamento)
        await self.db.flush()

        unit_amount = int(round(float(quota.importo_eur) * 100))
        stripe_session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": unit_amount,
                    "product_data": {"name": f"Quota associativa ASD Millennio — {categoria}"},
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
        pagamento.stripe_session_id = stripe_session.id
        await self.db.flush()

        return TesseramentoCheckoutResponse(
            tessera_id=tessera.id,
            pagamento_id=pagamento.id,
            stripe_checkout_url=stripe_session.url,
            importo_eur=float(quota.importo_eur),
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


    # ── verifica staff ────────────────────────────────────────────────────────

    async def lista_da_verificare(self) -> list:
        from schemas.tesseramento import (
            DocumentoBreve, SocioBreve, TesseramentoDaVerificare,
        )

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
            out.append(TesseramentoDaVerificare(
                tessera_id=t.id,
                numero_tessera=t.numero_tessera,
                categoria=t.sport,
                anno_sportivo=t.anno_sportivo,
                verifica_scadenza=t.verifica_scadenza,
                importo_eur=float(pag.importo_eur) if pag else None,
                socio=SocioBreve(
                    id=socio.id, nome=socio.nome, cognome=socio.cognome,
                    codice_fiscale=socio.codice_fiscale, is_minor=socio.is_minor,
                ),
                tutore=SocioBreve(
                    id=tutore.id, nome=tutore.nome, cognome=tutore.cognome,
                    codice_fiscale=tutore.codice_fiscale, is_minor=tutore.is_minor,
                ) if tutore else None,
                documenti=[DocumentoBreve(id=d.id, tipo=d.tipo, filename=d.filename) for d in docs],
            ))
        return out

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
        await self.db.flush()
        logger.info("Tesseramento %s confermato dallo staff.", tessera_id)

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
        if tessere:
            await self.db.flush()
        return len(tessere)

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
