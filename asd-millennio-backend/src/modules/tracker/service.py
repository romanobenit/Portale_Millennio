"""
Tracker iscritti: contatti interessati agli sport, con fonte e stato, per capire
quali sport e quali fonti portano iscritti paganti.

- Rita (ruolo `tracker`) e i dirigenti inseriscono e aggiornano i contatti.
- Ogni cambio di stato finisce nello storico: i conteggi usano le fasi raggiunte.
- I riepiloghi, i costi istruttore e la cancellazione su richiesta sono della dirigenza.
- Le righe non si cancellano (si passa a "perso"), salvo richiesta di rimozione
  dell'interessato o pulizia manuale dei "perso" da parte della dirigenza: allora
  la riga e il suo storico spariscono davvero.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from models.tracker import ContattoTracker, CostoIstruttore, MembroTracker, StatoContattoStorico
from modules.tracker.regole import (
    STATI_CHIUSI,
    ContattoConteggio,
    RigaConteggio,
    conteggia,
    costo_periodo,
    primo_del_mese,
    stesso_nome,
)
from schemas.tracker import (
    CambioStatoResponse,
    CancellaPersiResponse,
    ContattoCreate,
    ContattoDettaglioResponse,
    ContattoResponse,
    ContattoUpdate,
    CostoIstruttoreCreate,
    CostoIstruttoreResponse,
    ListaContattiResponse,
    MembroResponse,
    RiepilogoResponse,
    RigaRiepilogo,
)

TZ = ZoneInfo("Europe/Rome")
CAMPI_OBBLIGATORI = {"data_contatto", "sport", "fonte", "nome", "stato", "is_test"}


def oggi() -> date:
    return datetime.now(TZ).date()


def _nome_utente(user: dict) -> str:
    nome = user.get("name") or " ".join(
        p for p in (user.get("given_name"), user.get("family_name")) if p
    )
    return (nome or user.get("preferred_username") or "Utente").strip()[:120]


def _riga(sport: str, r: RigaConteggio, costo: Decimal | None) -> RigaRiepilogo:
    return RigaRiepilogo(
        sport=sport,
        lead=r.lead,
        prove_prenotate=r.prove_prenotate,
        prove_svolte=r.prove_svolte,
        iscritti=r.iscritti,
        paganti=r.paganti,
        persi=r.persi,
        conversione_pct=r.conversione_pct,
        incassato_eur=r.incassato_eur,
        impegnato_eur=r.impegnato_eur,
        costo_istruttore_eur=costo,
        margine_eur=None if costo is None else r.incassato_eur - costo,
    )


class TrackerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── membri ─────────────────────────────────────────────────────────────

    async def membro_corrente(self, user: dict) -> tuple[MembroTracker, bool]:
        """Registra (o aggiorna) chi accede: compare così fra i responsabili del follow-up."""
        dirigenza = "dirigenza" in user.get("realm_access", {}).get("roles", [])
        valori = dict(
            keycloak_user_id=user["sub"],
            nome=_nome_utente(user),
            ruolo="dirigenza" if dirigenza else "tracker",
        )
        stmt = insert(MembroTracker).values(**valori).on_conflict_do_update(
            index_elements=["keycloak_user_id"],
            set_={"nome": valori["nome"], "ruolo": valori["ruolo"], "ultimo_accesso": func.now()},
        ).returning(MembroTracker.id)
        membro_id = (await self.db.execute(stmt)).scalar_one()
        membro = await self.db.get(MembroTracker, membro_id, populate_existing=True)
        return membro, dirigenza

    async def membri(self) -> list[MembroResponse]:
        r = await self.db.execute(select(MembroTracker).order_by(MembroTracker.nome))
        return [MembroResponse.model_validate(m) for m in r.scalars().all()]

    async def _verifica_responsabile(self, responsabile_id: UUID | None) -> None:
        if responsabile_id and not await self.db.get(MembroTracker, responsabile_id):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Responsabile non valido")

    async def _nomi_membri(self, ids: set[UUID]) -> dict[UUID, str]:
        ids.discard(None)
        if not ids:
            return {}
        r = await self.db.execute(select(MembroTracker.id, MembroTracker.nome).where(MembroTracker.id.in_(ids)))
        return dict(r.all())

    # ─── contatti ───────────────────────────────────────────────────────────

    def _risposta(self, c: ContattoTracker, nomi: dict[UUID, str]) -> ContattoResponse:
        return ContattoResponse(
            id=c.id,
            data_contatto=c.data_contatto,
            sport=c.sport,
            fonte=c.fonte,
            nome=c.nome,
            canale=c.canale,
            recapito=c.recapito,
            stato=c.stato,
            data_prova=c.data_prova,
            tipo_abbonamento=c.tipo_abbonamento,
            importo_eur=c.importo_eur,
            responsabile_id=c.responsabile_id,
            responsabile_nome=nomi.get(c.responsabile_id),
            prossimo_followup=c.prossimo_followup,
            note=c.note,
            is_test=c.is_test,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )

    async def _risposte(self, contatti: list[ContattoTracker]) -> list[ContattoResponse]:
        nomi = await self._nomi_membri({c.responsabile_id for c in contatti})
        return [self._risposta(c, nomi) for c in contatti]

    async def _contatto(self, contatto_id: UUID, per_update: bool = False) -> ContattoTracker:
        q = select(ContattoTracker).where(ContattoTracker.id == contatto_id)
        if per_update:
            q = q.with_for_update()
        c = (await self.db.execute(q)).scalar_one_or_none()
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Contatto non trovato")
        return c

    async def lista(
        self,
        *,
        q: str | None,
        sport: str | None,
        fonte: str | None,
        stato: str | None,
        responsabile_id: UUID | None,
        test: bool,
        page: int,
        limit: int,
    ) -> ListaContattiResponse:
        filtri = [ContattoTracker.is_test.is_(test)]
        if q:
            like = f"%{q.strip()}%"
            filtri.append(or_(ContattoTracker.nome.ilike(like), ContattoTracker.recapito.ilike(like)))
        if sport:
            filtri.append(ContattoTracker.sport == sport)
        if fonte:
            filtri.append(ContattoTracker.fonte == fonte)
        if stato:
            filtri.append(ContattoTracker.stato == stato)
        if responsabile_id:
            filtri.append(ContattoTracker.responsabile_id == responsabile_id)
        totale = (await self.db.execute(select(func.count()).select_from(ContattoTracker).where(*filtri))).scalar_one()
        r = await self.db.execute(
            select(ContattoTracker)
            .where(*filtri)
            .order_by(ContattoTracker.data_contatto.desc(), ContattoTracker.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return ListaContattiResponse(
            contatti=await self._risposte(list(r.scalars().all())), totale=totale, page=page, limit=limit
        )

    async def dettaglio(self, contatto_id: UUID) -> ContattoDettaglioResponse:
        c = await self._contatto(contatto_id)
        storico = (
            await self.db.execute(
                select(StatoContattoStorico)
                .where(StatoContattoStorico.contatto_id == c.id)
                .order_by(StatoContattoStorico.cambiato_at)
            )
        ).scalars().all()
        nomi = await self._nomi_membri({c.responsabile_id} | {s.cambiato_da_id for s in storico})
        return ContattoDettaglioResponse(
            **self._risposta(c, nomi).model_dump(),
            storico=[
                CambioStatoResponse(stato=s.stato, cambiato_at=s.cambiato_at, cambiato_da=nomi.get(s.cambiato_da_id))
                for s in storico
            ],
        )

    async def possibili_doppioni(self, nome: str, escludi_id: UUID | None = None) -> list[ContattoResponse]:
        """Contatti con lo stesso nome (parole in qualsiasi ordine, senza accenti): "una riga per persona"."""
        parole = nome.split()
        if not parole:
            return []
        # Prefiltro sul database con la parola più lunga, confronto esatto in Python.
        chiave = max(parole, key=len)
        q = select(ContattoTracker).where(ContattoTracker.nome.ilike(f"%{chiave}%"))
        if escludi_id:
            q = q.where(ContattoTracker.id != escludi_id)
        candidati = (await self.db.execute(q.limit(200))).scalars().all()
        return await self._risposte([c for c in candidati if stesso_nome(c.nome, nome)])

    async def crea(self, data: ContattoCreate, membro: MembroTracker) -> ContattoResponse:
        await self._verifica_responsabile(data.responsabile_id)
        c = ContattoTracker(**data.model_dump(), creato_da_id=membro.id)
        self.db.add(c)
        await self.db.flush()
        self.db.add(StatoContattoStorico(contatto_id=c.id, stato=c.stato, cambiato_da_id=membro.id))
        await self.db.flush()
        await self.db.refresh(c)
        logger.info("Tracker: nuovo contatto %s (%s, %s)", c.id, c.sport, c.fonte)
        return (await self._risposte([c]))[0]

    async def aggiorna(self, contatto_id: UUID, data: ContattoUpdate, membro: MembroTracker) -> ContattoResponse:
        c = await self._contatto(contatto_id, per_update=True)
        modifiche = data.model_dump(exclude_unset=True)
        vuoti = [k for k in CAMPI_OBBLIGATORI if k in modifiche and modifiche[k] is None]
        if vuoti:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Campo obbligatorio: {', '.join(sorted(vuoti))}"
            )
        if "responsabile_id" in modifiche:
            await self._verifica_responsabile(modifiche["responsabile_id"])
        stato_prima = c.stato
        for campo, valore in modifiche.items():
            setattr(c, campo, valore)
        if c.stato != stato_prima:
            self.db.add(StatoContattoStorico(contatto_id=c.id, stato=c.stato, cambiato_da_id=membro.id))
        await self.db.flush()
        await self.db.refresh(c)
        return (await self._risposte([c]))[0]

    async def cancella_su_richiesta(self, contatto_id: UUID) -> None:
        """Rimozione richiesta dall'interessato (GDPR): riga e storico spariscono davvero."""
        c = await self._contatto(contatto_id, per_update=True)
        await self.db.execute(delete(StatoContattoStorico).where(StatoContattoStorico.contatto_id == c.id))
        await self.db.delete(c)
        await self.db.flush()
        logger.info("Tracker: contatto %s cancellato su richiesta dell'interessato", contatto_id)

    async def cancella_persi(self, fino_al: date, conferma: bool) -> CancellaPersiResponse:
        """
        Pulizia manuale della dirigenza: contatti oggi "perso" che ci sono passati entro
        `fino_al` (ora di Roma). Senza conferma restituisce solo quanti sono.
        """
        limite = datetime.combine(fino_al + timedelta(days=1), time(0), tzinfo=TZ)
        perso_at = (
            select(StatoContattoStorico.contatto_id, func.max(StatoContattoStorico.cambiato_at).label("perso_at"))
            .where(StatoContattoStorico.stato == "perso")
            .group_by(StatoContattoStorico.contatto_id)
            .subquery()
        )
        ids = list(
            (
                await self.db.execute(
                    select(ContattoTracker.id)
                    .join(perso_at, perso_at.c.contatto_id == ContattoTracker.id)
                    .where(ContattoTracker.stato == "perso", perso_at.c.perso_at < limite)
                )
            ).scalars().all()
        )
        if conferma and ids:
            await self.db.execute(delete(StatoContattoStorico).where(StatoContattoStorico.contatto_id.in_(ids)))
            await self.db.execute(delete(ContattoTracker).where(ContattoTracker.id.in_(ids)))
            await self.db.flush()
            logger.info("Tracker: cancellati %d contatti persi fino al %s", len(ids), fino_al)
        return CancellaPersiResponse(fino_al=fino_al, contatti=len(ids), cancellati=conferma and bool(ids))

    async def miei_followup(self, membro: MembroTracker) -> list[ContattoResponse]:
        """Follow-up aperti del membro: previsti per oggi o scaduti."""
        r = await self.db.execute(
            select(ContattoTracker)
            .where(
                ContattoTracker.responsabile_id == membro.id,
                ContattoTracker.prossimo_followup <= oggi(),
                ContattoTracker.stato.notin_(STATI_CHIUSI),
            )
            .order_by(ContattoTracker.prossimo_followup, ContattoTracker.nome)
        )
        return await self._risposte(list(r.scalars().all()))

    # ─── riepiloghi ─────────────────────────────────────────────────────────

    async def riepilogo(
        self, *, fonte: str | None, dal: date | None, al: date | None, solo_test: bool
    ) -> RiepilogoResponse:
        """
        Conteggi per sport dei contatti arrivati nel periodo (per data contatto).
        Con una fonte (es. Meta Ads) niente costo istruttore: il costo è dello sport, non della fonte.
        """
        filtri = [ContattoTracker.is_test.is_(solo_test)]
        if fonte:
            filtri.append(ContattoTracker.fonte == fonte)
        if dal:
            filtri.append(ContattoTracker.data_contatto >= dal)
        if al:
            filtri.append(ContattoTracker.data_contatto <= al)
        r = await self.db.execute(
            select(
                ContattoTracker.sport,
                ContattoTracker.stato,
                ContattoTracker.importo_eur,
                ContattoTracker.data_contatto,
                func.array_agg(StatoContattoStorico.stato),
            )
            .outerjoin(StatoContattoStorico, StatoContattoStorico.contatto_id == ContattoTracker.id)
            .where(*filtri)
            .group_by(ContattoTracker.id)
        )
        righe_db = r.all()
        contatti = [
            ContattoConteggio(sport=sport, stato=stato, stati_raggiunti={s for s in storico if s}, importo_eur=importo)
            for sport, stato, importo, _, storico in righe_db
        ]
        conteggi = conteggia(contatti)

        costi: dict[str, Decimal] | None = None
        if not fonte:
            inizio = dal or min((d for *_, d, _ in righe_db), default=None)
            fine = al or oggi()
            costi = {s: Decimal("0.00") for s in conteggi}
            if inizio and inizio <= fine:
                variazioni = (await self.db.execute(select(CostoIstruttore))).scalars().all()
                for s in costi:
                    costi[s] = costo_periodo(
                        [(v.valido_dal, Decimal(v.costo_mensile_eur)) for v in variazioni if v.sport == s],
                        inizio,
                        fine,
                    )

        totale = RigaConteggio()
        for riga in conteggi.values():
            totale.somma(riga)
        return RiepilogoResponse(
            fonte=fonte,
            dal=dal,
            al=al,
            solo_test=solo_test,
            righe=[_riga(s, riga, None if costi is None else costi[s]) for s, riga in conteggi.items()],
            totale=_riga("totale", totale, None if costi is None else sum(costi.values(), Decimal("0.00"))),
        )

    # ─── costi istruttore ───────────────────────────────────────────────────

    async def costi(self) -> list[CostoIstruttoreResponse]:
        r = await self.db.execute(select(CostoIstruttore).order_by(CostoIstruttore.sport, CostoIstruttore.valido_dal))
        return [CostoIstruttoreResponse.model_validate(c) for c in r.scalars().all()]

    async def imposta_costo(self, data: CostoIstruttoreCreate) -> CostoIstruttoreResponse:
        """Nuova variazione (o correzione di quella dello stesso mese)."""
        stmt = (
            insert(CostoIstruttore)
            .values(sport=data.sport, valido_dal=primo_del_mese(data.valido_dal), costo_mensile_eur=data.costo_mensile_eur)
            .on_conflict_do_update(
                constraint="uq_costo_istruttore_sport_mese",
                set_={"costo_mensile_eur": data.costo_mensile_eur, "created_at": datetime.now(timezone.utc)},
            )
            .returning(CostoIstruttore.id)
        )
        costo_id = (await self.db.execute(stmt)).scalar_one()
        costo = await self.db.get(CostoIstruttore, costo_id, populate_existing=True)
        return CostoIstruttoreResponse.model_validate(costo)

    async def elimina_costo(self, costo_id: UUID) -> None:
        costo = await self.db.get(CostoIstruttore, costo_id)
        if not costo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Costo non trovato")
        await self.db.delete(costo)
        await self.db.flush()
