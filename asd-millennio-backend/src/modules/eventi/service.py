import asyncio
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import stripe
from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from models.evento import EventoCampo, ListaAttesaEvento, PrenotazioneEvento
from models.socio import Socio
from models.tessera import Tessera
from models.tessera_esterna import TesseraEsterna
from modules.credito.service import CreditoService
from modules.eventi import email as eventi_email
from schemas.eventi import (
    EventoCreate,
    EventoDettaglioResponse,
    EventoDirigenzaResponse,
    EventoPubblicoResponse,
    EventoUpdate,
    InAttesaResponse,
    MiaPrenotazioneEventoResponse,
    MieiEventiResponse,
    PartecipanteResponse,
    PrenotaEventoResponse,
    PrenotazioneEventoResponse,
    SegnaPresenzaRequest,
    SocioRicercaResponse,
)

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

TZ = ZoneInfo("Europe/Rome")
# Stripe impone expires_at ≥ 30 minuti dalla creazione: il posto resta trattenuto
# esattamente quanto la sessione, così non si può pagare un posto già rilasciato.
LOCK_MINUTES = 31
MAX_ASSENZE = 2
STATI_ATTIVI = ("in_attesa_pagamento", "confermata")


def inizio_evento(ev: EventoCampo) -> datetime:
    return datetime.combine(ev.data, ev.ora_inizio, tzinfo=TZ)


def fine_evento(ev: EventoCampo) -> datetime:
    return datetime.combine(ev.data, ev.ora_fine, tzinfo=TZ)


def scadenza_annullamento(ev: EventoCampo) -> datetime:
    """Si annulla fino alla fine del giorno precedente l'evento (ora italiana)."""
    return datetime.combine(ev.data, time.min, tzinfo=TZ)


def solo_online(assenze: int) -> bool:
    return assenze >= MAX_ASSENZE


def fine_abilitazione(tessere: list[tuple[str, date | None]], scadenze_esterne: list[date]) -> date | None:
    """
    Fino a quale data si possono usare i campi (None = non abilitato).
    `tessere`: (categoria, scadenza) delle tessere ATTIVE; `scadenze_esterne`: scadenze
    delle tessere di altre ASD non rifiutate, che contano solo con l'iscrizione community.
    """
    fini = [scad or date.max for sport, scad in tessere if sport != "community"]
    if any(sport == "community" for sport, _ in tessere):
        fini += scadenze_esterne
    return max(fini) if fini else None


def motivo_non_abilitato(fino_al: date | None) -> str:
    if fino_al is None:
        return ("Per prenotare serve la tessera Millennio oppure l'iscrizione community "
                "con la tessera di un'altra ASD.")
    return (f"La tessera vale fino al {fino_al.strftime('%d/%m/%Y')}: per questo evento "
            "va rinnovata o aggiornata da «Le mie tessere».")


def calcola_posti(ev: EventoCampo, c: dict) -> tuple[int, int]:
    """(partecipanti, posti_liberi). I checkout in corso occupano un posto ma non sono partecipanti."""
    partecipanti = c["online"] + c["in_sede"] + (ev.presenze_manuali or 0)
    liberi = max(ev.posti_max - partecipanti - c["lock"], 0)
    return partecipanti, liberi


class EventiService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── helpers ────────────────────────────────────────────────────────────

    async def _conteggi(self, evento_ids: list[UUID]) -> dict[UUID, dict]:
        out = {eid: {"online": 0, "in_sede": 0, "lock": 0, "attesa": 0} for eid in evento_ids}
        if not evento_ids:
            return out
        now = datetime.now(timezone.utc)
        confermata = PrenotazioneEvento.stato == "confermata"
        r = await self.db.execute(
            select(
                PrenotazioneEvento.evento_id,
                func.count().filter(and_(confermata, PrenotazioneEvento.modalita == "online")),
                func.count().filter(and_(confermata, PrenotazioneEvento.modalita == "in_sede")),
                func.count().filter(
                    and_(
                        PrenotazioneEvento.stato == "in_attesa_pagamento",
                        PrenotazioneEvento.bloccata_fino_a > now,
                    )
                ),
            )
            .where(PrenotazioneEvento.evento_id.in_(evento_ids))
            .group_by(PrenotazioneEvento.evento_id)
        )
        for eid, online, in_sede, lock in r.all():
            out[eid].update(online=online, in_sede=in_sede, lock=lock)
        r = await self.db.execute(
            select(ListaAttesaEvento.evento_id, func.count())
            .where(ListaAttesaEvento.evento_id.in_(evento_ids))
            .group_by(ListaAttesaEvento.evento_id)
        )
        for eid, n in r.all():
            out[eid]["attesa"] = n
        return out

    @staticmethod
    def _campi_pubblici(ev: EventoCampo, c: dict) -> dict:
        partecipanti, liberi = calcola_posti(ev, c)
        return dict(
            id=ev.id,
            titolo=ev.titolo,
            sport=list(ev.sport or []),
            data=ev.data,
            ora_inizio=ev.ora_inizio,
            ora_fine=ev.ora_fine,
            prezzo_eur=Decimal(ev.prezzo_eur),
            posti_max=ev.posti_max,
            partecipanti=partecipanti,
            posti_liberi=liberi,
            in_lista_attesa=c["attesa"],
            completo=liberi == 0,
            stato=ev.stato,
        )

    def _pubblico(self, ev: EventoCampo, c: dict) -> EventoPubblicoResponse:
        return EventoPubblicoResponse(**self._campi_pubblici(ev, c))

    def _dirigenza(self, ev: EventoCampo, c: dict) -> EventoDirigenzaResponse:
        return EventoDirigenzaResponse(
            **self._campi_pubblici(ev, c),
            presenze_manuali=ev.presenze_manuali or 0,
            confermati_online=c["online"],
            confermati_in_sede=c["in_sede"],
            note=ev.note,
        )

    async def _assenze(self, socio_ids: list[UUID]) -> dict[UUID, int]:
        out = {sid: 0 for sid in socio_ids}
        if not socio_ids:
            return out
        r = await self.db.execute(
            select(PrenotazioneEvento.socio_id, func.count())
            .join(Socio, Socio.id == PrenotazioneEvento.socio_id)
            .where(
                PrenotazioneEvento.socio_id.in_(socio_ids),
                PrenotazioneEvento.modalita == "in_sede",
                PrenotazioneEvento.stato == "confermata",
                PrenotazioneEvento.presenza == "assente",
                or_(
                    Socio.assenze_azzerate_at.is_(None),
                    PrenotazioneEvento.presenza_segnata_at > Socio.assenze_azzerate_at,
                ),
            )
            .group_by(PrenotazioneEvento.socio_id)
        )
        out.update(dict(r.all()))
        return out

    async def _abilitati_fino_al(self, socio_ids: list[UUID]) -> dict[UUID, date | None]:
        if not socio_ids:
            return {}
        tessere: dict[UUID, list] = {sid: [] for sid in socio_ids}
        r = await self.db.execute(
            select(Tessera.socio_id, Tessera.sport, Tessera.data_scadenza)
            .where(Tessera.socio_id.in_(socio_ids), Tessera.stato == "attiva")
        )
        for sid, sport, scad in r.all():
            tessere[sid].append((sport, scad))
        esterne: dict[UUID, list] = {sid: [] for sid in socio_ids}
        r = await self.db.execute(
            select(TesseraEsterna.socio_id, TesseraEsterna.data_scadenza)
            .where(TesseraEsterna.socio_id.in_(socio_ids), TesseraEsterna.verifica_stato != "rifiutata")
        )
        for sid, scad in r.all():
            esterne[sid].append(scad)
        return {sid: fine_abilitazione(tessere[sid], esterne[sid]) for sid in socio_ids}

    async def _evento_per_update(self, evento_id: UUID) -> EventoCampo:
        ev = (
            await self.db.execute(select(EventoCampo).where(EventoCampo.id == evento_id).with_for_update())
        ).scalar_one_or_none()
        if not ev:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Evento non trovato")
        return ev

    @staticmethod
    def _verifica_prenotabile(ev: EventoCampo) -> None:
        if ev.stato != "programmato":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="L'evento è stato annullato")
        if fine_evento(ev) <= datetime.now(TZ):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="L'evento è già concluso")

    async def _scadi_lock(self, *, evento_id: UUID | None = None, socio_id: UUID | None = None) -> None:
        now = datetime.now(timezone.utc)
        q = select(PrenotazioneEvento).where(
            PrenotazioneEvento.stato == "in_attesa_pagamento",
            PrenotazioneEvento.bloccata_fino_a <= now,
        )
        if evento_id:
            q = q.where(PrenotazioneEvento.evento_id == evento_id)
        if socio_id:
            q = q.where(PrenotazioneEvento.socio_id == socio_id)
        scadute = (await self.db.execute(q)).scalars().all()
        for p in scadute:
            p.stato = "scaduta"
        if scadute:
            await self.db.flush()

    async def _prenotazione_attiva(self, evento_id: UUID, socio_id: UUID) -> PrenotazioneEvento | None:
        return (
            await self.db.execute(
                select(PrenotazioneEvento).where(
                    PrenotazioneEvento.evento_id == evento_id,
                    PrenotazioneEvento.socio_id == socio_id,
                    PrenotazioneEvento.stato.in_(STATI_ATTIVI),
                )
            )
        ).scalar_one_or_none()

    async def _rimuovi_da_lista_attesa(self, evento_id: UUID, socio_id: UUID) -> None:
        await self.db.execute(
            delete(ListaAttesaEvento).where(
                ListaAttesaEvento.evento_id == evento_id, ListaAttesaEvento.socio_id == socio_id
            )
        )

    async def _rimborsa(self, pren: PrenotazioneEvento) -> None:
        """Rimborso totale Stripe. Idempotente: un rimborso già eseguito non è un errore."""
        if not pren.stripe_payment_intent_id:
            return
        try:
            await asyncio.to_thread(stripe.Refund.create, payment_intent=pren.stripe_payment_intent_id)
        except stripe.error.InvalidRequestError as e:
            if getattr(e, "code", None) == "charge_already_refunded":
                return
            logger.error("Rimborso Stripe fallito per prenotazione evento %s: %s", pren.id, e)
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Rimborso non riuscito: riprova tra qualche minuto o contatta la segreteria.",
            )
        logger.info("Rimborso eseguito: prenotazione evento %s", pren.id)

    async def _chiudi_sessione_stripe(self, session_id: str | None) -> None:
        if not session_id:
            return
        try:
            sess = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
            if getattr(sess, "status", None) == "open":
                await asyncio.to_thread(stripe.checkout.Session.expire, session_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("Impossibile scadere la sessione Stripe %s: %s", session_id, e)

    async def _url_sessione_aperta(self, session_id: str | None) -> str | None:
        if not session_id:
            return None
        try:
            sess = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("Sessione Stripe %s non recuperabile: %s", session_id, e)
            return None
        if getattr(sess, "status", None) == "open":
            return getattr(sess, "url", None)
        return None

    async def _notifica_posto_libero(self, ev: EventoCampo) -> None:
        """Avvisa TUTTA la lista d'attesa: il posto va a chi conferma per primo."""
        if ev.stato != "programmato" or fine_evento(ev) <= datetime.now(TZ):
            return
        c = (await self._conteggi([ev.id]))[ev.id]
        if calcola_posti(ev, c)[1] <= 0 or c["attesa"] == 0:
            return
        rows = (
            await self.db.execute(
                select(ListaAttesaEvento, Socio)
                .join(Socio, Socio.id == ListaAttesaEvento.socio_id)
                .where(ListaAttesaEvento.evento_id == ev.id)
                .order_by(ListaAttesaEvento.created_at)
            )
        ).all()
        now = datetime.now(timezone.utc)
        for voce, socio in rows:
            if await eventi_email.invia_posto_libero(to=socio.email, nome=socio.nome, evento=ev):
                voce.notificato_at = now
        await self.db.flush()
        logger.info("Posto libero notificato a %s persone in lista d'attesa (evento %s)", len(rows), ev.id)

    # ─── pubblico ───────────────────────────────────────────────────────────

    async def lista_pubblica(self, limit: int = 30) -> list[EventoPubblicoResponse]:
        now_local = datetime.now(TZ)
        r = await self.db.execute(
            select(EventoCampo)
            .where(EventoCampo.stato == "programmato", EventoCampo.data >= now_local.date())
            .order_by(EventoCampo.data, EventoCampo.ora_inizio)
            .limit(limit)
        )
        eventi = [e for e in r.scalars().all() if fine_evento(e) > now_local]
        conteggi = await self._conteggi([e.id for e in eventi])
        return [self._pubblico(e, conteggi[e.id]) for e in eventi]

    # ─── socio ──────────────────────────────────────────────────────────────

    async def prenota(
        self, socio: Socio, evento_id: UUID, modalita: str, *, da_staff: bool = False, usa_credito: bool = False
    ) -> PrenotaEventoResponse:
        if usa_credito and (modalita != "online" or da_staff):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Il credito si usa solo per pagare online")
        ev = await self._evento_per_update(evento_id)
        self._verifica_prenotabile(ev)
        await self._scadi_lock(evento_id=ev.id)

        esistente = await self._prenotazione_attiva(ev.id, socio.id)
        if esistente:
            if esistente.stato == "in_attesa_pagamento" and modalita == "online" and not da_staff and not usa_credito:
                url = await self._url_sessione_aperta(esistente.stripe_session_id)
                if url:
                    return PrenotaEventoResponse(
                        prenotazione=PrenotazioneEventoResponse.model_validate(esistente),
                        stripe_checkout_url=url,
                    )
            if esistente.stato == "in_attesa_pagamento":
                # checkout precedente non più pagabile o cambio modalità: lo chiudo e riparto
                await self._chiudi_sessione_stripe(esistente.stripe_session_id)
                esistente.stato = "annullata"
                await self.db.flush()
            else:
                raise HTTPException(status.HTTP_409_CONFLICT, detail="Hai già una prenotazione per questo evento")

        fino_al = (await self._abilitati_fino_al([socio.id]))[socio.id]
        if fino_al is None or ev.data > fino_al:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=motivo_non_abilitato(fino_al))

        c = (await self._conteggi([ev.id]))[ev.id]
        if calcola_posti(ev, c)[1] <= 0:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Evento al completo: puoi iscriverti alla lista d'attesa",
            )

        if modalita == "in_sede":
            if solo_online((await self._assenze([socio.id]))[socio.id]):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Hai {MAX_ASSENZE} assenze su prenotazioni da pagare in sede: per ora puoi "
                        "prenotare solo pagando online. Per lo sblocco contatta la dirigenza."
                    ),
                )
            pren = PrenotazioneEvento(
                evento_id=ev.id,
                socio_id=socio.id,
                modalita="in_sede",
                stato="confermata",
                importo_eur=ev.prezzo_eur,
                inserita_da_staff=da_staff,
            )
            await self._inserisci(pren)
            await self._rimuovi_da_lista_attesa(ev.id, socio.id)
            await self.db.flush()
            await self.db.refresh(pren)
            logger.info("Prenotazione evento in sede: evento=%s prenotazione=%s", ev.id, pren.id)
            return PrenotaEventoResponse(prenotazione=PrenotazioneEventoResponse.model_validate(pren))

        if usa_credito and Decimal(ev.prezzo_eur) > 0:
            pren = PrenotazioneEvento(
                evento_id=ev.id, socio_id=socio.id, modalita="online", stato="confermata",
                importo_eur=ev.prezzo_eur, pagato_con_credito=True,
            )
            await self._inserisci(pren)
            await CreditoService(self.db).addebita_evento(
                socio.id, pren.id, Decimal(ev.prezzo_eur), eventi_email.descrivi_evento(ev)
            )
            await self._rimuovi_da_lista_attesa(ev.id, socio.id)
            await self.db.flush()
            await self.db.refresh(pren)
            logger.info("Prenotazione evento pagata col credito: evento=%s prenotazione=%s", ev.id, pren.id)
            return PrenotaEventoResponse(prenotazione=PrenotazioneEventoResponse.model_validate(pren))

        if Decimal(ev.prezzo_eur) == 0:
            pren = PrenotazioneEvento(
                evento_id=ev.id, socio_id=socio.id, modalita="online", stato="confermata", importo_eur=0
            )
            await self._inserisci(pren)
            await self._rimuovi_da_lista_attesa(ev.id, socio.id)
            await self.db.flush()
            await self.db.refresh(pren)
            return PrenotaEventoResponse(prenotazione=PrenotazioneEventoResponse.model_validate(pren))

        lock_fino = datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)
        pren = PrenotazioneEvento(
            evento_id=ev.id,
            socio_id=socio.id,
            modalita="online",
            stato="in_attesa_pagamento",
            importo_eur=ev.prezzo_eur,
            bloccata_fino_a=lock_fino,
        )
        await self._inserisci(pren)

        metadata = {"tipo": "evento", "prenotazione_evento_id": str(pren.id)}
        try:
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": int((Decimal(ev.prezzo_eur) * 100).to_integral_value()),
                        "product_data": {
                            "name": "Ingresso evento Palasirio",
                            "description": eventi_email.descrivi_evento(ev),
                        },
                    },
                    "quantity": 1,
                }],
                customer_email=socio.email,
                expires_at=int(lock_fino.timestamp()),
                success_url=f"{settings.app_url}/dashboard/prenotazioni?status=success",
                cancel_url=f"{settings.app_url}/dashboard/prenotazioni?status=cancel",
                metadata=metadata,
                payment_intent_data={"metadata": metadata},
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Creazione sessione Stripe evento fallita: %s", e)
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Pagamento online momentaneamente non disponibile, riprova tra poco.",
            )
        pren.stripe_session_id = session["id"]
        await self.db.flush()
        await self.db.refresh(pren)
        logger.info("Checkout evento avviato: evento=%s prenotazione=%s", ev.id, pren.id)
        return PrenotaEventoResponse(
            prenotazione=PrenotazioneEventoResponse.model_validate(pren),
            stripe_checkout_url=session["url"],
        )

    async def _inserisci(self, pren: PrenotazioneEvento) -> None:
        self.db.add(pren)
        try:
            await self.db.flush()
        except IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Hai già una prenotazione per questo evento")

    async def conferma_pagamento(self, stripe_session_id: str) -> None:
        """Webhook checkout.session.completed (tipo=evento), con doppia verifica via Stripe API."""
        pren = await self._prenotazione_da_sessione(stripe_session_id)
        if not pren:
            logger.warning("Pagamento evento: nessuna prenotazione per la sessione %s", stripe_session_id)
            return
        ev = await self._evento_per_update(pren.evento_id)
        await self.db.refresh(pren, with_for_update=True)
        if pren.stato in ("confermata", "rimborsata"):
            return

        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, stripe_session_id)
        if getattr(session, "payment_status", None) != "paid":
            return
        pren.stripe_payment_intent_id = session.payment_intent

        if pren.stato == "in_attesa_pagamento":
            pren.stato = "confermata"
            pren.bloccata_fino_a = None
        else:
            # Pagamento arrivato dopo il rilascio del posto (o dopo un annullamento):
            # confermo solo se c'è ancora posto, altrimenti rimborso.
            c = (await self._conteggi([ev.id]))[ev.id]
            altra = await self._prenotazione_attiva(ev.id, pren.socio_id)
            if ev.stato == "programmato" and calcola_posti(ev, c)[1] > 0 and not altra:
                pren.stato = "confermata"
                pren.bloccata_fino_a = None
            else:
                await self._rimborsa(pren)
                pren.stato = "rimborsata"
                logger.warning("Pagamento evento tardivo rimborsato: prenotazione %s", pren.id)
        if pren.stato == "confermata":
            await self._rimuovi_da_lista_attesa(ev.id, pren.socio_id)
        await self.db.flush()
        logger.info("Prenotazione evento %s → %s", pren.id, pren.stato)

    async def _prenotazione_da_sessione(self, stripe_session_id: str) -> PrenotazioneEvento | None:
        return (
            await self.db.execute(
                select(PrenotazioneEvento).where(PrenotazioneEvento.stripe_session_id == stripe_session_id)
            )
        ).scalar_one_or_none()

    async def gestisci_sessione_scaduta(self, stripe_session_id: str) -> None:
        pren = await self._prenotazione_da_sessione(stripe_session_id)
        if not pren:
            return
        ev = await self._evento_per_update(pren.evento_id)
        await self.db.refresh(pren, with_for_update=True)
        if pren.stato != "in_attesa_pagamento":
            return
        pren.stato = "scaduta"
        await self.db.flush()
        await self._notifica_posto_libero(ev)

    async def segna_rimborso_esterno(self, payment_intent_id: str) -> None:
        """Webhook charge.refunded: rimborso eseguito anche da dashboard Stripe."""
        pren = (
            await self.db.execute(
                select(PrenotazioneEvento).where(PrenotazioneEvento.stripe_payment_intent_id == payment_intent_id)
            )
        ).scalar_one_or_none()
        if not pren:
            return
        ev = await self._evento_per_update(pren.evento_id)
        await self.db.refresh(pren, with_for_update=True)
        if pren.stato == "rimborsata":
            return
        era_confermata = pren.stato == "confermata"
        pren.stato = "rimborsata"
        await self.db.flush()
        if era_confermata:
            await self._notifica_posto_libero(ev)

    async def _rimborsa_in_credito(self, pren: PrenotazioneEvento, ev: EventoCampo, motivo: str) -> None:
        await CreditoService(self.db).rimborsa_evento(
            pren.socio_id, pren.id, Decimal(pren.importo_eur), f"{motivo}: {eventi_email.descrivi_evento(ev)}"
        )

    async def annulla(
        self, socio_id: UUID, prenotazione_id: UUID, *, rimborso: str = "carta"
    ) -> PrenotazioneEventoResponse:
        pren = (
            await self.db.execute(
                select(PrenotazioneEvento).where(
                    PrenotazioneEvento.id == prenotazione_id, PrenotazioneEvento.socio_id == socio_id
                )
            )
        ).scalar_one_or_none()
        if not pren:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Prenotazione non trovata")
        ev = await self._evento_per_update(pren.evento_id)
        await self.db.refresh(pren, with_for_update=True)

        if pren.stato == "in_attesa_pagamento":
            await self._chiudi_sessione_stripe(pren.stripe_session_id)
            pren.stato = "annullata"
        elif pren.stato == "confermata":
            if datetime.now(TZ) >= scadenza_annullamento(ev):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="Si può annullare solo entro il giorno prima dell'evento",
                )
            if pren.pagato_con_credito or (
                rimborso == "credito" and pren.modalita == "online" and pren.stripe_payment_intent_id
            ):
                await self._rimborsa_in_credito(pren, ev, "Annullamento")
                pren.stato = "rimborsata"
            elif pren.modalita == "online" and pren.stripe_payment_intent_id:
                await self._rimborsa(pren)
                pren.stato = "rimborsata"
            else:
                pren.stato = "annullata"
        else:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Questa prenotazione non è più attiva")

        await self.db.flush()
        await self._notifica_posto_libero(ev)
        await self.db.refresh(pren)
        logger.info("Prenotazione evento annullata: %s → %s", pren.id, pren.stato)
        return PrenotazioneEventoResponse.model_validate(pren)

    async def iscrivi_lista_attesa(self, socio_id: UUID, evento_id: UUID) -> None:
        ev = await self._evento_per_update(evento_id)
        self._verifica_prenotabile(ev)
        await self._scadi_lock(evento_id=ev.id)
        if await self._prenotazione_attiva(ev.id, socio_id):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Sei già prenotato per questo evento")
        fino_al = (await self._abilitati_fino_al([socio_id]))[socio_id]
        if fino_al is None or ev.data > fino_al:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=motivo_non_abilitato(fino_al))
        c = (await self._conteggi([ev.id]))[ev.id]
        if calcola_posti(ev, c)[1] > 0:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Ci sono ancora posti liberi: prenota direttamente")
        gia = (
            await self.db.execute(
                select(ListaAttesaEvento.id).where(
                    ListaAttesaEvento.evento_id == ev.id, ListaAttesaEvento.socio_id == socio_id
                )
            )
        ).scalar_one_or_none()
        if not gia:
            self.db.add(ListaAttesaEvento(evento_id=ev.id, socio_id=socio_id))
            await self.db.flush()

    async def esci_lista_attesa(self, socio_id: UUID, evento_id: UUID) -> None:
        await self._rimuovi_da_lista_attesa(evento_id, socio_id)
        await self.db.flush()

    async def miei_eventi(self, socio: Socio) -> MieiEventiResponse:
        await self._scadi_lock(socio_id=socio.id)
        now_local = datetime.now(TZ)
        rows = (
            await self.db.execute(
                select(PrenotazioneEvento, EventoCampo)
                .join(EventoCampo, EventoCampo.id == PrenotazioneEvento.evento_id)
                .where(
                    PrenotazioneEvento.socio_id == socio.id,
                    PrenotazioneEvento.stato.in_(STATI_ATTIVI),
                    EventoCampo.data >= now_local.date(),
                )
                .order_by(EventoCampo.data, EventoCampo.ora_inizio)
            )
        ).all()
        rows = [(p, e) for p, e in rows if fine_evento(e) > now_local]
        conteggi = await self._conteggi([e.id for _, e in rows])
        prenotazioni = [
            MiaPrenotazioneEventoResponse(
                **PrenotazioneEventoResponse.model_validate(p).model_dump(),
                evento=self._pubblico(e, conteggi[e.id]),
                annullabile=(p.stato == "in_attesa_pagamento")
                or (p.stato == "confermata" and now_local < scadenza_annullamento(e)),
            )
            for p, e in rows
        ]
        attesa = (
            await self.db.execute(select(ListaAttesaEvento.evento_id).where(ListaAttesaEvento.socio_id == socio.id))
        ).scalars().all()
        assenze = (await self._assenze([socio.id]))[socio.id]
        return MieiEventiResponse(
            prenotazioni=prenotazioni,
            lista_attesa=list(attesa),
            assenze=assenze,
            solo_online=solo_online(assenze),
            abilitato_fino_al=(await self._abilitati_fino_al([socio.id]))[socio.id],
            saldo_credito_eur=await CreditoService(self.db).saldo(socio.id),
        )

    # ─── dirigenza ──────────────────────────────────────────────────────────

    async def crea_evento(self, data: EventoCreate) -> EventoDirigenzaResponse:
        ev = EventoCampo(**data.model_dump(), presenze_manuali=0, stato="programmato")
        self.db.add(ev)
        await self.db.flush()
        await self.db.refresh(ev)
        logger.info("Evento creato: %s (%s)", ev.id, ev.data)
        return self._dirigenza(ev, (await self._conteggi([ev.id]))[ev.id])

    async def aggiorna_evento(self, evento_id: UUID, data: EventoUpdate) -> EventoDirigenzaResponse:
        ev = await self._evento_per_update(evento_id)
        if ev.stato != "programmato":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Un evento annullato non si può modificare")
        for campo, valore in data.model_dump(exclude_unset=True).items():
            if valore is not None or campo in ("titolo", "note"):
                setattr(ev, campo, valore)
        if ev.ora_fine <= ev.ora_inizio:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="L'ora di fine deve essere successiva all'ora di inizio",
            )
        c = (await self._conteggi([ev.id]))[ev.id]
        occupati = c["online"] + c["in_sede"] + c["lock"] + (ev.presenze_manuali or 0)
        if ev.posti_max < occupati:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Ci sono già {occupati} posti occupati: i posti non possono scendere sotto questo numero",
            )
        await self.db.flush()
        await self.db.refresh(ev)
        await self._notifica_posto_libero(ev)
        return self._dirigenza(ev, (await self._conteggi([ev.id]))[ev.id])

    async def annulla_evento(self, evento_id: UUID) -> EventoDirigenzaResponse:
        ev = await self._evento_per_update(evento_id)
        if ev.stato == "annullato":
            return self._dirigenza(ev, (await self._conteggi([ev.id]))[ev.id])
        rows = (
            await self.db.execute(
                select(PrenotazioneEvento, Socio)
                .join(Socio, Socio.id == PrenotazioneEvento.socio_id)
                .where(PrenotazioneEvento.evento_id == ev.id, PrenotazioneEvento.stato.in_(STATI_ATTIVI))
                .with_for_update(of=PrenotazioneEvento)
            )
        ).all()
        da_avvisare: list[tuple[Socio, bool, bool]] = []
        for pren, socio in rows:
            if pren.stato == "in_attesa_pagamento":
                await self._chiudi_sessione_stripe(pren.stripe_session_id)
                pren.stato = "annullata"
                continue
            rimborso = pren.pagato_con_credito or (pren.modalita == "online" and bool(pren.stripe_payment_intent_id))
            if pren.pagato_con_credito:
                await self._rimborsa_in_credito(pren, ev, "Evento annullato")
                pren.stato = "rimborsata"
            elif rimborso:
                await self._rimborsa(pren)
                pren.stato = "rimborsata"
            else:
                pren.stato = "annullata"
            da_avvisare.append((socio, rimborso, pren.pagato_con_credito))
        ev.stato = "annullato"
        await self.db.execute(delete(ListaAttesaEvento).where(ListaAttesaEvento.evento_id == ev.id))
        await self.db.flush()
        for socio, rimborso, in_credito in da_avvisare:
            await eventi_email.invia_evento_annullato(
                to=socio.email, nome=socio.nome, evento=ev, rimborso=rimborso, in_credito=in_credito
            )
        logger.info("Evento %s annullato: %s partecipanti avvisati", ev.id, len(da_avvisare))
        await self.db.refresh(ev)
        return self._dirigenza(ev, (await self._conteggi([ev.id]))[ev.id])

    async def lista_dirigenza(self, data_inizio: date, data_fine: date) -> list[EventoDirigenzaResponse]:
        await self._scadi_lock()
        r = await self.db.execute(
            select(EventoCampo)
            .where(EventoCampo.data >= data_inizio, EventoCampo.data <= data_fine)
            .order_by(EventoCampo.data, EventoCampo.ora_inizio)
        )
        eventi = r.scalars().all()
        conteggi = await self._conteggi([e.id for e in eventi])
        return [self._dirigenza(e, conteggi[e.id]) for e in eventi]

    async def dettaglio(self, evento_id: UUID) -> EventoDettaglioResponse:
        await self._scadi_lock(evento_id=evento_id)
        ev = (await self.db.execute(select(EventoCampo).where(EventoCampo.id == evento_id))).scalar_one_or_none()
        if not ev:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Evento non trovato")
        rows = (
            await self.db.execute(
                select(PrenotazioneEvento, Socio)
                .join(Socio, Socio.id == PrenotazioneEvento.socio_id)
                .where(PrenotazioneEvento.evento_id == ev.id, PrenotazioneEvento.stato.in_(STATI_ATTIVI))
                .order_by(Socio.cognome, Socio.nome)
            )
        ).all()
        attesa = (
            await self.db.execute(
                select(ListaAttesaEvento, Socio)
                .join(Socio, Socio.id == ListaAttesaEvento.socio_id)
                .where(ListaAttesaEvento.evento_id == ev.id)
                .order_by(ListaAttesaEvento.created_at)
            )
        ).all()
        assenze = await self._assenze([s.id for _, s in rows])
        partecipanti = [
            PartecipanteResponse(
                prenotazione_id=p.id,
                socio_id=s.id,
                nome=s.nome,
                cognome=s.cognome,
                modalita=p.modalita,
                stato=p.stato,
                importo_eur=Decimal(p.importo_eur),
                pagato_in_sede=p.pagato_in_sede,
                presenza=p.presenza,
                inserita_da_staff=p.inserita_da_staff,
                assenze=assenze[s.id],
                solo_online=solo_online(assenze[s.id]),
            )
            for p, s in rows
        ]
        return EventoDettaglioResponse(
            evento=self._dirigenza(ev, (await self._conteggi([ev.id]))[ev.id]),
            partecipanti=partecipanti,
            lista_attesa=[
                InAttesaResponse(
                    socio_id=s.id, nome=s.nome, cognome=s.cognome,
                    iscritto_at=v.created_at, notificato_at=v.notificato_at,
                )
                for v, s in attesa
            ],
        )

    async def aggiungi_partecipante(self, evento_id: UUID, socio_id: UUID) -> PrenotaEventoResponse:
        socio = (await self.db.execute(select(Socio).where(Socio.id == socio_id))).scalar_one_or_none()
        if not socio:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")
        return await self.prenota(socio, evento_id, "in_sede", da_staff=True)

    async def segna(self, prenotazione_id: UUID, req: SegnaPresenzaRequest) -> PrenotazioneEventoResponse:
        pren = (
            await self.db.execute(
                select(PrenotazioneEvento).where(PrenotazioneEvento.id == prenotazione_id).with_for_update()
            )
        ).scalar_one_or_none()
        if not pren:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Prenotazione non trovata")
        if pren.stato != "confermata":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="La prenotazione non è confermata")
        ev = (await self.db.execute(select(EventoCampo).where(EventoCampo.id == pren.evento_id))).scalar_one()

        presenza = req.presenza if "presenza" in req.model_fields_set else pren.presenza
        pagato = req.pagato_in_sede if req.pagato_in_sede is not None else pren.pagato_in_sede
        if pagato and pren.modalita != "in_sede":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Questa prenotazione è già stata pagata online")
        if presenza == "assente":
            if pagato:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail="Chi ha pagato in sede non può risultare assente"
                )
            if datetime.now(TZ) < inizio_evento(ev):
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail="L'assenza si può segnare solo dall'inizio dell'evento"
                )
        if "presenza" in req.model_fields_set and presenza != pren.presenza:
            pren.presenza = presenza
            pren.presenza_segnata_at = datetime.now(timezone.utc) if presenza else None
        pren.pagato_in_sede = pagato
        await self.db.flush()
        await self.db.refresh(pren)
        return PrenotazioneEventoResponse.model_validate(pren)

    async def imposta_presenze_manuali(self, evento_id: UUID, valore: int) -> EventoDirigenzaResponse:
        ev = await self._evento_per_update(evento_id)
        ev.presenze_manuali = valore
        await self.db.flush()
        await self.db.refresh(ev)
        await self._notifica_posto_libero(ev)
        return self._dirigenza(ev, (await self._conteggi([ev.id]))[ev.id])

    async def azzera_assenze(self, socio_id: UUID) -> None:
        socio = (await self.db.execute(select(Socio).where(Socio.id == socio_id))).scalar_one_or_none()
        if not socio:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")
        socio.assenze_azzerate_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("Assenze azzerate per il socio %s", socio_id)

    async def cerca_soci(self, q: str) -> list[SocioRicercaResponse]:
        termine = f"%{q.strip()}%"
        r = await self.db.execute(
            select(Socio)
            .where(
                or_(
                    func.concat(Socio.nome, " ", Socio.cognome).ilike(termine),
                    func.concat(Socio.cognome, " ", Socio.nome).ilike(termine),
                    Socio.codice_fiscale.ilike(termine),
                    Socio.email.ilike(termine),
                ),
            )
            .order_by(Socio.cognome, Socio.nome)
            .limit(10)
        )
        soci = r.scalars().all()
        ids = [s.id for s in soci]
        abilitati = await self._abilitati_fino_al(ids)
        assenze = await self._assenze(ids)
        return [
            SocioRicercaResponse(
                id=s.id, nome=s.nome, cognome=s.cognome, codice_fiscale=s.codice_fiscale,
                abilitato_fino_al=abilitati[s.id], assenze=assenze[s.id], solo_online=solo_online(assenze[s.id]),
            )
            for s in soci
        ]
