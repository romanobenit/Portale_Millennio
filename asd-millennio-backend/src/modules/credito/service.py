"""
Credito interno: un registro di movimenti per i servizi dell'associazione.

Non è una moneta: niente trasferimenti fra soci, niente prelievi, nessun
circuito esterno. Entra con accrediti e ricariche (in sede o, se attivata,
online con Stripe) ed esce solo pagando servizi della Millennio (per ora gli
ingressi agli eventi). Ogni operazione sul saldo di un socio è serializzata
con un advisory lock, così il saldo non può andare sotto zero per una corsa.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import stripe
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from models.credito import MovimentoCredito
from models.socio import Socio
from schemas.credito import (
    MioCreditoResponse,
    MovimentoCreditoResponse,
    MovimentoDirigenzaCreate,
    RiepilogoCreditoResponse,
    SaldoSocioResponse,
    SchedaCreditoSocioResponse,
    TotalePerTipo,
)

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

def euro(valore: Decimal) -> str:
    return f"€ {valore:.2f}".replace(".", ",")


class CreditoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── registro ───────────────────────────────────────────────────────────

    async def _blocca(self, socio_id: UUID) -> None:
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"credito:{socio_id}"}
        )

    async def saldo(self, socio_id: UUID) -> Decimal:
        s = (
            await self.db.execute(
                select(func.coalesce(func.sum(MovimentoCredito.importo_eur), 0)).where(
                    MovimentoCredito.socio_id == socio_id
                )
            )
        ).scalar_one()
        return Decimal(s).quantize(Decimal("0.01"))

    async def _registra(
        self,
        socio_id: UUID,
        tipo: str,
        importo: Decimal,
        *,
        causale: str | None = None,
        operatore_id: UUID | None = None,
        prenotazione_evento_id: UUID | None = None,
        stripe_session_id: str | None = None,
        stripe_payment_intent_id: str | None = None,
        tetto: bool = False,
        consenti_negativo: bool = False,
    ) -> MovimentoCredito:
        """Aggiunge un movimento (importo con segno). Va chiamata con il lock del socio."""
        importo = Decimal(importo).quantize(Decimal("0.01"))
        saldo_dopo = await self.saldo(socio_id) + importo
        if saldo_dopo < 0 and not consenti_negativo:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Credito insufficiente")
        if tetto and saldo_dopo > settings.credito_saldo_max_eur:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Il credito non può superare {euro(Decimal(settings.credito_saldo_max_eur))}",
            )
        m = MovimentoCredito(
            socio_id=socio_id, tipo=tipo, importo_eur=importo, saldo_dopo_eur=saldo_dopo, causale=causale,
            operatore_id=operatore_id, prenotazione_evento_id=prenotazione_evento_id,
            stripe_session_id=stripe_session_id, stripe_payment_intent_id=stripe_payment_intent_id,
        )
        self.db.add(m)
        await self.db.flush()
        logger.info("Credito: movimento %s %s su socio %s → saldo %s", tipo, importo, socio_id, saldo_dopo)
        return m

    async def _movimenti(self, socio_id: UUID, limite: int) -> list[MovimentoCreditoResponse]:
        r = await self.db.execute(
            select(MovimentoCredito)
            .where(MovimentoCredito.socio_id == socio_id)
            .order_by(MovimentoCredito.created_at.desc())
            .limit(limite)
        )
        return [MovimentoCreditoResponse.model_validate(m) for m in r.scalars().all()]

    # ─── eventi ─────────────────────────────────────────────────────────────

    async def addebita_evento(self, socio_id: UUID, prenotazione_id: UUID, importo: Decimal, descrizione: str) -> None:
        await self._blocca(socio_id)
        await self._registra(
            socio_id, "pagamento_evento", -Decimal(importo),
            causale=descrizione, prenotazione_evento_id=prenotazione_id,
        )

    async def rimborsa_evento(self, socio_id: UUID, prenotazione_id: UUID, importo: Decimal, descrizione: str) -> None:
        await self._blocca(socio_id)
        gia = (
            await self.db.execute(
                select(MovimentoCredito.id).where(
                    MovimentoCredito.prenotazione_evento_id == prenotazione_id,
                    MovimentoCredito.tipo == "rimborso_evento",
                )
            )
        ).scalar_one_or_none()
        if gia:
            return
        await self._registra(
            socio_id, "rimborso_evento", Decimal(importo),
            causale=descrizione, prenotazione_evento_id=prenotazione_id,
        )

    # ─── socio ──────────────────────────────────────────────────────────────

    async def mio(self, socio: Socio) -> MioCreditoResponse:
        return MioCreditoResponse(
            saldo_eur=await self.saldo(socio.id),
            movimenti=await self._movimenti(socio.id, 50),
            ricarica_online_attiva=settings.credito_ricarica_online_attiva,
            ricarica_min_eur=settings.credito_ricarica_min_eur,
            ricarica_max_eur=settings.credito_ricarica_max_eur,
            saldo_max_eur=settings.credito_saldo_max_eur,
        )

    async def avvia_ricarica(self, socio: Socio, importo_eur: int) -> str:
        if not settings.credito_ricarica_online_attiva:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="La ricarica online non è attiva: puoi ricaricare il credito in sede.",
            )
        if not settings.credito_ricarica_min_eur <= importo_eur <= settings.credito_ricarica_max_eur:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"La ricarica va da {settings.credito_ricarica_min_eur} "
                    f"a {settings.credito_ricarica_max_eur} euro"
                ),
            )
        if await self.saldo(socio.id) + importo_eur > settings.credito_saldo_max_eur:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Il credito non può superare {euro(Decimal(settings.credito_saldo_max_eur))}",
            )
        metadata = {"tipo": "ricarica_credito", "socio_id": str(socio.id), "importo_eur": str(importo_eur)}
        try:
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": importo_eur * 100,
                        "product_data": {
                            "name": "Ricarica credito ASD Millennio",
                            "description": "Credito utilizzabile solo per i servizi dell'associazione",
                        },
                    },
                    "quantity": 1,
                }],
                customer_email=socio.email,
                expires_at=int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
                success_url=f"{settings.app_url}/dashboard/credito?status=success",
                cancel_url=f"{settings.app_url}/dashboard/credito?status=cancel",
                metadata=metadata,
                payment_intent_data={"metadata": metadata},
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Creazione sessione Stripe ricarica credito fallita: %s", e)
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Pagamento online momentaneamente non disponibile, riprova tra poco.",
            )
        logger.info("Checkout ricarica credito avviato: socio=%s importo=%s", socio.id, importo_eur)
        return session["url"]

    async def conferma_ricarica(self, stripe_session_id: str) -> None:
        """Webhook checkout.session.completed (tipo=ricarica_credito), con doppia verifica via Stripe API."""
        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, stripe_session_id)
        if getattr(session, "payment_status", None) != "paid":
            return
        meta = session.to_dict().get("metadata") or {}
        if meta.get("tipo") != "ricarica_credito" or not meta.get("socio_id"):
            logger.error("Ricarica credito: metadata non validi nella sessione %s", stripe_session_id)
            return
        socio_id = UUID(meta["socio_id"])
        await self._blocca(socio_id)
        gia = (
            await self.db.execute(
                select(MovimentoCredito.id).where(MovimentoCredito.stripe_session_id == stripe_session_id)
            )
        ).scalar_one_or_none()
        if gia:
            return
        # Quanto è stato davvero incassato, non quanto dichiarato nei metadata
        importo = (Decimal(session.amount_total) / 100).quantize(Decimal("0.01"))
        await self._registra(
            socio_id, "ricarica_online", importo, causale="Ricarica online (carta)",
            stripe_session_id=stripe_session_id, stripe_payment_intent_id=session.payment_intent,
        )

    async def segna_rimborso_ricarica(self, payment_intent_id: str, rimborsato_cent: int) -> None:
        """Webhook charge.refunded su una ricarica: toglie dal credito quanto rimborsato sulla carta."""
        ricarica = (
            await self.db.execute(
                select(MovimentoCredito).where(
                    MovimentoCredito.stripe_payment_intent_id == payment_intent_id,
                    MovimentoCredito.tipo == "ricarica_online",
                )
            )
        ).scalar_one_or_none()
        if not ricarica:
            return
        await self._blocca(ricarica.socio_id)
        gia_stornato = -(
            await self.db.execute(
                select(func.coalesce(func.sum(MovimentoCredito.importo_eur), 0)).where(
                    MovimentoCredito.stripe_payment_intent_id == payment_intent_id,
                    MovimentoCredito.tipo == "storno",
                )
            )
        ).scalar_one()
        da_stornare = (Decimal(rimborsato_cent) / 100).quantize(Decimal("0.01")) - Decimal(gia_stornato)
        if da_stornare <= 0:
            return
        m = await self._registra(
            ricarica.socio_id, "storno", -da_stornare, causale="Ricarica rimborsata sulla carta",
            stripe_payment_intent_id=payment_intent_id, consenti_negativo=True,
        )
        if m.saldo_dopo_eur < 0:
            logger.warning("Credito negativo dopo il rimborso di una ricarica: socio %s", ricarica.socio_id)

    # ─── dirigenza ──────────────────────────────────────────────────────────

    async def registra_dirigenza(
        self, socio_id: UUID, dati: MovimentoDirigenzaCreate, operatore_id: UUID | None
    ) -> SchedaCreditoSocioResponse:
        if not (await self.db.execute(select(Socio.id).where(Socio.id == socio_id))).scalar_one_or_none():
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")
        causale = (dati.causale or "").strip() or None
        if dati.tipo in ("accredito", "storno") and (not causale or len(causale) < 3):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Indica la causale del movimento")
        importo = Decimal(dati.importo_eur)
        await self._blocca(socio_id)
        await self._registra(
            socio_id, dati.tipo, -importo if dati.tipo == "storno" else importo,
            causale=causale or ("Ricarica in sede" if dati.tipo == "ricarica_sede" else None),
            operatore_id=operatore_id, tetto=dati.tipo == "ricarica_sede",
        )
        return await self.scheda(socio_id)

    async def scheda(self, socio_id: UUID) -> SchedaCreditoSocioResponse:
        s = (await self.db.execute(select(Socio).where(Socio.id == socio_id))).scalar_one_or_none()
        if not s:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")
        return SchedaCreditoSocioResponse(
            socio_id=s.id, nome=s.nome, cognome=s.cognome, codice_fiscale=s.codice_fiscale,
            saldo_eur=await self.saldo(s.id), movimenti=await self._movimenti(s.id, 100),
        )

    async def cerca(self, q: str) -> list[SaldoSocioResponse]:
        termine = f"%{q.strip()}%"
        saldi = (
            select(MovimentoCredito.socio_id, func.sum(MovimentoCredito.importo_eur).label("saldo"))
            .group_by(MovimentoCredito.socio_id)
            .subquery()
        )
        r = await self.db.execute(
            select(Socio, func.coalesce(saldi.c.saldo, 0))
            .outerjoin(saldi, saldi.c.socio_id == Socio.id)
            .where(or_(
                func.concat(Socio.nome, " ", Socio.cognome).ilike(termine),
                func.concat(Socio.cognome, " ", Socio.nome).ilike(termine),
                Socio.codice_fiscale.ilike(termine),
            ))
            .order_by(Socio.cognome, Socio.nome)
            .limit(15)
        )
        return [
            SaldoSocioResponse(
                socio_id=s.id, nome=s.nome, cognome=s.cognome, codice_fiscale=s.codice_fiscale,
                saldo_eur=Decimal(saldo).quantize(Decimal("0.01")),
            )
            for s, saldo in r.all()
        ]

    async def riepilogo(self) -> RiepilogoCreditoResponse:
        saldi = (
            select(MovimentoCredito.socio_id, func.sum(MovimentoCredito.importo_eur).label("saldo"))
            .group_by(MovimentoCredito.socio_id)
            .subquery()
        )
        totale, con_saldo = (
            await self.db.execute(
                select(func.coalesce(func.sum(saldi.c.saldo), 0), func.count().filter(saldi.c.saldo > 0))
            )
        ).one()
        da = datetime.now(timezone.utc) - timedelta(days=30)
        per_tipo = (
            await self.db.execute(
                select(MovimentoCredito.tipo, func.count(), func.sum(MovimentoCredito.importo_eur))
                .where(MovimentoCredito.created_at >= da)
                .group_by(MovimentoCredito.tipo)
                .order_by(MovimentoCredito.tipo)
            )
        ).all()
        return RiepilogoCreditoResponse(
            credito_in_circolo_eur=Decimal(totale).quantize(Decimal("0.01")),
            soci_con_saldo=con_saldo,
            ultimi_30gg=[
                TotalePerTipo(tipo=t, movimenti=n, totale_eur=Decimal(s).quantize(Decimal("0.01")))
                for t, n, s in per_tipo
            ],
            ricarica_online_attiva=settings.credito_ricarica_online_attiva,
        )
