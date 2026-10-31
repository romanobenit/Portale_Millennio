from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from models.pickleball import (
    ConfigPickleball,
    GiocatoreOspite,
    GiocatorePartita,
    PartitaPickleball,
    ProfiloAtleta,
    RatingOspite,
    RatingPickleball,
    TorneoPickleball,
)
from models.socio import Socio
from modules.eventi.service import EventiService
from modules.pickleball.elo import (
    PARTITE_PROVVISORIE,
    applica_partita,
    vincitore_da_punteggi,
)
from modules.pickleball.regole import config_completa, eta_nell_anno, sesso_da_cf
from schemas.pickleball import (
    DashboardPickleballDirigenza,
    GiocatoreBreve,
    GiocatoreRicerca,
    MioPickleballResponse,
    PartitaCreate,
    PartitaDirigenzaCreate,
    PartitaResponse,
    ProfiloAtletaResponse,
    ProfiloAtletaUpdate,
    PuntoAndamento,
    RigaClassifica,
    SettimanaPartite,
    StatisticheFormato,
)

FORMATI = ("singolo", "doppio")


def nome_breve(s: Socio) -> str:
    return f"{s.nome} {s.cognome[:1]}." if s.cognome else s.nome


def nome_ospite(o: GiocatoreOspite, completo: bool) -> str:
    if completo:
        return f"{o.nome} {o.cognome} (ospite{', ' + o.club if o.club else ''})"
    return f"{o.nome} {o.cognome[:1]}. (ospite)"


class PickleballService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── helpers ────────────────────────────────────────────────────────────

    async def config(self) -> dict:
        riga = (await self.db.execute(select(ConfigPickleball).where(ConfigPickleball.id == 1))).scalar_one_or_none()
        return config_completa(riga.valori if riga else None)

    async def _soci(self, ids) -> dict[UUID, Socio]:
        ids = [i for i in set(ids) if i]
        if not ids:
            return {}
        r = await self.db.execute(select(Socio).where(Socio.id.in_(ids)))
        return {s.id: s for s in r.scalars().all()}

    async def _ospiti(self, ids) -> dict[UUID, GiocatoreOspite]:
        ids = [i for i in set(ids) if i]
        if not ids:
            return {}
        r = await self.db.execute(select(GiocatoreOspite).where(GiocatoreOspite.id.in_(ids)))
        return {o.id: o for o in r.scalars().all()}

    async def nomi(self, soci_ids, ospiti_ids, *, completi: bool) -> dict[UUID, str]:
        soci, ospiti = await self._soci(soci_ids), await self._ospiti(ospiti_ids)
        out = {sid: (f"{s.nome} {s.cognome}" if completi else nome_breve(s)) for sid, s in soci.items()}
        out.update({oid: nome_ospite(o, completi) for oid, o in ospiti.items()})
        return out

    async def _verifica_giocatori(self, ids: list[UUID], *, ammetti_ospiti: bool = False) -> set[UUID]:
        """Verifica che esistano tutti; ritorna gli id che sono ospiti."""
        if len(set(ids)) != len(ids):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lo stesso giocatore compare due volte")
        soci = await self._soci(ids)
        ospiti = set((await self._ospiti(ids)).keys()) if ammetti_ospiti else set()
        if len(soci) + len(ospiti) != len(ids):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Giocatore non trovato")
        return ospiti

    async def _verifica_abilitato(self, socio: Socio) -> None:
        fino = (await EventiService(self.db)._abilitati_fino_al([socio.id]))[socio.id]
        if fino is None or fino < date.today():
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Per registrare partite serve la tessera Millennio o l'iscrizione community in corso di validità.",
            )

    async def _giocatori(self, partita_ids: list[UUID]) -> dict[UUID, list[GiocatorePartita]]:
        out: dict = defaultdict(list)
        if not partita_ids:
            return out
        r = await self.db.execute(select(GiocatorePartita).where(GiocatorePartita.partita_id.in_(partita_ids)))
        for g in r.scalars().all():
            out[g.partita_id].append(g)
        return out

    async def _partita_per_update(self, partita_id: UUID) -> PartitaPickleball:
        p = (
            await self.db.execute(
                select(PartitaPickleball).where(PartitaPickleball.id == partita_id).with_for_update()
            )
        ).scalar_one_or_none()
        if not p:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Partita non trovata")
        return p

    async def risposte(
        self, partite: list[PartitaPickleball], *, viewer_id: UUID | None = None, nomi_completi: bool = False
    ) -> list[PartitaResponse]:
        gioc = await self._giocatori([p.id for p in partite])
        tutti = [g for lst in gioc.values() for g in lst]
        nomi = await self.nomi([g.socio_id for g in tutti], [g.ospite_id for g in tutti], completi=nomi_completi)
        tornei_ids = {p.torneo_id for p in partite if p.torneo_id}
        tornei = {}
        if tornei_ids:
            r = await self.db.execute(select(TorneoPickleball.id, TorneoPickleball.nome).where(TorneoPickleball.id.in_(tornei_ids)))
            tornei = dict(r.all())
        out = []
        for p in partite:
            lst = gioc[p.id]
            squadra_ins = next((g.squadra for g in lst if g.socio_id == p.inserita_da), None)
            mia = next((g.squadra for g in lst if g.socio_id == viewer_id), None)
            out.append(PartitaResponse(
                id=p.id, formato=p.formato, data=p.data, punteggi=p.punteggi, vincitore=p.vincitore,
                stato=p.stato, torneo=tornei.get(p.torneo_id, p.torneo), torneo_id=p.torneo_id,
                categoria=p.categoria, fase=p.fase, walkover=p.walkover, fuori_classifica=p.fuori_classifica,
                inserita_da_dirigenza=p.inserita_da_dirigenza, note=p.note, created_at=p.created_at,
                giocatori=[
                    GiocatoreBreve(
                        socio_id=g.socio_id, ospite_id=g.ospite_id, ospite=g.ospite_id is not None,
                        nome=nomi.get(g.giocatore_id, "—"),
                        squadra=g.squadra,
                        rating_prima=float(g.rating_prima) if g.rating_prima is not None else None,
                        rating_dopo=float(g.rating_dopo) if g.rating_dopo is not None else None,
                    )
                    for g in sorted(lst, key=lambda g: g.squadra)
                ],
                da_confermare=(
                    p.stato == "in_attesa_conferma" and mia is not None
                    and squadra_ins is not None and mia != squadra_ins
                ),
            ))
        return out

    async def crea_partita(
        self, *, formato: str, data: date, squadra_a: list[UUID], squadra_b: list[UUID], punteggi: list,
        confermata: bool, inserita_da: UUID | None, dirigenza: bool, ospiti: set[UUID] = frozenset(),
        torneo: str | None = None, note: str | None = None, torneo_id: UUID | None = None,
        categoria: str | None = None, fase: str | None = None, walkover: bool = False,
        vincitore: str | None = None, ricalcola: bool = True,
    ) -> PartitaPickleball:
        if walkover:
            if vincitore not in ("a", "b"):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Walkover: indica il vincitore")
            punteggi = []
        else:
            try:
                vincitore = vincitore_da_punteggi(punteggi)
            except ValueError as e:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        if data > date.today():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La data della partita non può essere futura")
        now = datetime.now(timezone.utc)
        p = PartitaPickleball(
            formato=formato, data=data, punteggi=punteggi, vincitore=vincitore,
            stato="confermata" if confermata else "in_attesa_conferma",
            torneo=torneo, note=note, inserita_da=inserita_da, inserita_da_dirigenza=dirigenza,
            confermata_da=inserita_da if confermata else None, confermata_at=now if confermata else None,
            torneo_id=torneo_id, categoria=categoria, fase=fase, walkover=walkover,
        )
        self.db.add(p)
        await self.db.flush()
        for squadra, ids in (("a", squadra_a), ("b", squadra_b)):
            for gid in ids:
                if gid in ospiti:
                    self.db.add(GiocatorePartita(partita_id=p.id, ospite_id=gid, squadra=squadra))
                else:
                    self.db.add(GiocatorePartita(partita_id=p.id, socio_id=gid, squadra=squadra))
        await self.db.flush()
        if confermata and ricalcola:
            await self.ricalcola(formato)
        return p

    # ─── classifica (ricalcolo completo) ────────────────────────────────────

    async def ricalcola(self, formato: str) -> None:
        """
        Ricostruisce la classifica del formato rigiocando in ordine tutte le partite confermate.
        Non contano: i walkover e le amichevoli oltre il limite settimanale contro lo stesso avversario.
        Le partite di torneo pesano `peso_torneo` volte un'amichevole.
        """
        await self.db.execute(text("SELECT pg_advisory_xact_lock(hashtext('ricalcolo_pickleball'))"))
        cfg = await self.config()
        partite = (
            await self.db.execute(
                select(PartitaPickleball)
                .where(PartitaPickleball.formato == formato, PartitaPickleball.stato == "confermata")
                .order_by(PartitaPickleball.data, PartitaPickleball.confermata_at, PartitaPickleball.created_at)
            )
        ).scalars().all()
        gioc = await self._giocatori([p.id for p in partite])

        stato: dict = {}
        ospiti: set = set()
        agg: dict = defaultdict(lambda: {"max": 0.0, "vittorie": 0, "ultima": None})
        amichevoli: Counter = Counter()      # (anno, settimana, coppia di avversari) -> amichevoli contate
        for p in partite:
            lst = gioc[p.id]
            for g in lst:
                g.rating_prima = g.rating_dopo = None
            a = [g.giocatore_id for g in lst if g.squadra == "a"]
            b = [g.giocatore_id for g in lst if g.squadra == "b"]
            if p.walkover or not a or not b:
                p.fuori_classifica = "walkover"
                continue
            if p.torneo_id is None:
                settimana = p.data.isocalendar()[:2]
                coppie = [(settimana, frozenset((x, y))) for x in a for y in b]
                if any(amichevoli[c] >= cfg["amichevoli_max_settimana"] for c in coppie):
                    p.fuori_classifica = "limite amichevoli"
                    continue
                for c in coppie:
                    amichevoli[c] += 1
            p.fuori_classifica = None
            peso = cfg["peso_torneo"] if p.torneo_id else 1.0
            variazioni = applica_partita(stato, a, b, p.vincitore, peso)
            for g in lst:
                if g.ospite_id:
                    ospiti.add(g.ospite_id)
                g.rating_prima, g.rating_dopo = variazioni[g.giocatore_id]
                x = agg[g.giocatore_id]
                x["max"] = max(x["max"], g.rating_dopo)
                x["vittorie"] += 1 if g.squadra == p.vincitore else 0
                x["ultima"] = p.data

        non_confermate = select(PartitaPickleball.id).where(
            PartitaPickleball.formato == formato, PartitaPickleball.stato != "confermata"
        )
        await self.db.execute(
            update(GiocatorePartita)
            .where(GiocatorePartita.partita_id.in_(non_confermate))
            .values(rating_prima=None, rating_dopo=None)
        )
        await self.db.execute(
            update(PartitaPickleball)
            .where(PartitaPickleball.formato == formato, PartitaPickleball.stato != "confermata")
            .values(fuori_classifica=None)
        )
        await self.db.execute(delete(RatingPickleball).where(RatingPickleball.formato == formato))
        await self.db.execute(delete(RatingOspite).where(RatingOspite.formato == formato))
        for gid, s in stato.items():
            if gid in ospiti:
                self.db.add(RatingOspite(
                    ospite_id=gid, formato=formato, rating=s["rating"], partite=s["partite"],
                    vittorie=agg[gid]["vittorie"],
                ))
            else:
                self.db.add(RatingPickleball(
                    socio_id=gid, formato=formato, rating=s["rating"], rating_max=agg[gid]["max"],
                    partite=s["partite"], vittorie=agg[gid]["vittorie"], ultima_partita=agg[gid]["ultima"],
                ))
        await self.db.flush()
        logger.info("Classifica pickleball %s ricalcolata: %d partite, %d giocatori", formato, len(partite), len(stato))

    async def classifica(
        self, formato: str, *, completa: bool = False, limite: int | None = None,
        sesso: str | None = None, eta_min: int | None = None,
    ) -> list[RigaClassifica]:
        """
        Classifica Elo dei soci (gli ospiti non compaiono). Per i soci: niente minori, niente profili
        nascosti, niente inattivi. `completa` (dirigenza) mostra tutti, con nomi per esteso.
        Sesso e fascia d'età sono ricavati da codice fiscale e data di nascita.
        """
        cfg = await self.config()
        q = (
            select(RatingPickleball, Socio, ProfiloAtleta)
            .join(Socio, Socio.id == RatingPickleball.socio_id)
            .outerjoin(ProfiloAtleta, ProfiloAtleta.socio_id == RatingPickleball.socio_id)
            .where(RatingPickleball.formato == formato, RatingPickleball.partite > 0)
            .order_by(RatingPickleball.rating.desc())
        )
        if not completa:
            q = q.where(Socio.is_minor.is_(False)).where(
                (ProfiloAtleta.visibile_in_classifica.is_(None)) | (ProfiloAtleta.visibile_in_classifica.is_(True))
            )
        oggi = date.today()
        soglia_attivita = oggi - timedelta(days=cfg["giorni_inattivita"])
        righe = []
        for r, s, prof in (await self.db.execute(q)).all():
            inattivo = r.ultima_partita is None or r.ultima_partita < soglia_attivita
            if inattivo and not completa:
                continue
            if sesso and sesso_da_cf(s.codice_fiscale) != sesso:
                continue
            if eta_min and (eta_nell_anno(s.data_nascita, oggi.year) or 0) < eta_min:
                continue
            dupr = None
            if prof is not None:
                dupr = prof.dupr_singolo if formato == "singolo" else prof.dupr_doppio
            righe.append(RigaClassifica(
                posizione=len(righe) + 1, socio_id=s.id, nome=f"{s.nome} {s.cognome}" if completa else nome_breve(s),
                rating=float(r.rating), rating_max=float(r.rating_max), partite=r.partite, vittorie=r.vittorie,
                provvisorio=r.partite < PARTITE_PROVVISORIE, dupr=float(dupr) if dupr is not None else None,
                inattivo=inattivo,
            ))
            if limite and len(righe) >= limite:
                break
        return righe

    # ─── socio ──────────────────────────────────────────────────────────────

    async def registra_socio(self, socio: Socio, dati: PartitaCreate) -> PartitaResponse:
        await self._verifica_abilitato(socio)
        squadra_a = [socio.id] + ([dati.compagno_id] if dati.compagno_id else [])
        squadra_b = list(dati.avversari_ids)
        await self._verifica_giocatori(squadra_a + squadra_b)
        p = await self.crea_partita(
            formato=dati.formato, data=dati.data, squadra_a=squadra_a, squadra_b=squadra_b,
            punteggi=dati.punteggi, confermata=False, inserita_da=socio.id, dirigenza=False,
        )
        await self.db.refresh(p)
        return (await self.risposte([p], viewer_id=socio.id))[0]

    async def _squadre(self, p: PartitaPickleball, socio_id: UUID) -> tuple[str | None, str | None]:
        lst = (await self._giocatori([p.id]))[p.id]
        return (
            next((g.squadra for g in lst if g.socio_id == p.inserita_da), None),
            next((g.squadra for g in lst if g.socio_id == socio_id), None),
        )

    async def conferma(self, socio: Socio, partita_id: UUID) -> None:
        p = await self._partita_per_update(partita_id)
        if p.stato != "in_attesa_conferma":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="La partita non è in attesa di conferma")
        sq_ins, mia = await self._squadre(p, socio.id)
        if mia is None or mia == sq_ins:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Può confermare solo un avversario")
        p.stato = "confermata"
        p.confermata_da = socio.id
        p.confermata_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.ricalcola(p.formato)

    async def contesta(self, socio: Socio, partita_id: UUID, motivo: str) -> None:
        p = await self._partita_per_update(partita_id)
        if p.stato != "in_attesa_conferma":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="La partita non è in attesa di conferma")
        sq_ins, mia = await self._squadre(p, socio.id)
        if mia is None or mia == sq_ins:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Può contestare solo un avversario")
        p.stato = "contestata"
        p.note = f"Contestata da {nome_breve(socio)}: {motivo.strip()}"
        await self.db.flush()

    async def ritira(self, socio: Socio, partita_id: UUID) -> None:
        p = await self._partita_per_update(partita_id)
        if p.inserita_da != socio.id or p.stato not in ("in_attesa_conferma", "contestata"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Puoi ritirare solo una tua partita non ancora confermata")
        p.stato = "annullata"
        await self.db.flush()

    async def _profilo(self, socio_id: UUID) -> ProfiloAtleta | None:
        return (
            await self.db.execute(select(ProfiloAtleta).where(ProfiloAtleta.socio_id == socio_id))
        ).scalar_one_or_none()

    @staticmethod
    def _profilo_response(p: ProfiloAtleta | None) -> ProfiloAtletaResponse:
        if p is None:
            return ProfiloAtletaResponse(
                visibile_in_classifica=True, obiettivo_singolo=None, obiettivo_doppio=None,
                obiettivo_partite_mese=None, dupr_id=None, dupr_singolo=None, dupr_doppio=None,
            )
        return ProfiloAtletaResponse(
            visibile_in_classifica=p.visibile_in_classifica, obiettivo_singolo=p.obiettivo_singolo,
            obiettivo_doppio=p.obiettivo_doppio, obiettivo_partite_mese=p.obiettivo_partite_mese,
            dupr_id=p.dupr_id,
            dupr_singolo=float(p.dupr_singolo) if p.dupr_singolo is not None else None,
            dupr_doppio=float(p.dupr_doppio) if p.dupr_doppio is not None else None,
        )

    async def aggiorna_profilo(self, socio: Socio, dati: ProfiloAtletaUpdate) -> ProfiloAtletaResponse:
        p = await self._profilo(socio.id)
        if p is None:
            p = ProfiloAtleta(socio_id=socio.id, visibile_in_classifica=True)
            self.db.add(p)
        for campo, valore in dati.model_dump(exclude_unset=True).items():
            if campo == "visibile_in_classifica" and valore is None:
                continue
            setattr(p, campo, valore)
        await self.db.flush()
        return self._profilo_response(p)

    async def mio(self, socio: Socio) -> MioPickleballResponse:
        prof = await self._profilo(socio.id)
        mie = (
            await self.db.execute(
                select(PartitaPickleball)
                .join(GiocatorePartita, GiocatorePartita.partita_id == PartitaPickleball.id)
                .where(GiocatorePartita.socio_id == socio.id, PartitaPickleball.stato != "annullata")
                .order_by(PartitaPickleball.data.desc(), PartitaPickleball.created_at.desc())
            )
        ).scalars().all()
        gioc = await self._giocatori([p.id for p in mie])
        confermate = [p for p in mie if p.stato == "confermata"]
        giocate = [p for p in confermate if not p.walkover]

        statistiche = {}
        for formato in FORMATI:
            r = (
                await self.db.execute(
                    select(RatingPickleball).where(
                        RatingPickleball.socio_id == socio.id, RatingPickleball.formato == formato
                    )
                )
            ).scalar_one_or_none()
            posizione = None
            if r:
                # posizione nella classifica che vedono gli altri soci; se non vi compare, in quella completa
                for completa in (False, True):
                    posizione = next(
                        (c.posizione for c in await self.classifica(formato, completa=completa)
                         if c.socio_id == socio.id),
                        None,
                    )
                    if posizione:
                        break
            andamento = [
                PuntoAndamento(data=p.data, rating=float(g.rating_dopo))
                for p in reversed(confermate) if p.formato == formato
                for g in gioc[p.id] if g.socio_id == socio.id and g.rating_dopo is not None
            ]
            obiettivo = None
            if prof is not None:
                obiettivo = prof.obiettivo_singolo if formato == "singolo" else prof.obiettivo_doppio
            statistiche[formato] = StatisticheFormato(
                formato=formato,
                rating=float(r.rating) if r else None,
                rating_max=float(r.rating_max) if r else None,
                posizione=posizione,
                partite=r.partite if r else 0,
                vittorie=r.vittorie if r else 0,
                provvisorio=(r.partite if r else 0) < PARTITE_PROVVISORIE,
                obiettivo=obiettivo,
                andamento=andamento,
            )

        inizio_mese = date.today().replace(day=1)
        serie = 0
        compagni, avversari = Counter(), Counter()
        for p in giocate:
            mia = next(g.squadra for g in gioc[p.id] if g.socio_id == socio.id)
            for g in gioc[p.id]:
                if g.socio_id != socio.id:
                    (compagni if g.squadra == mia else avversari)[g.giocatore_id] += 1
        for p in giocate:
            mia = next(g.squadra for g in gioc[p.id] if g.socio_id == socio.id)
            if mia != p.vincitore:
                break
            serie += 1
        frequenti = list(compagni) + list(avversari)
        nomi = await self.nomi(frequenti, frequenti, completi=False)

        def piu_frequente(c: Counter) -> str | None:
            if not c:
                return None
            gid, n = c.most_common(1)[0]
            return f"{nomi[gid]} ({n})" if gid in nomi else None

        risposte = await self.risposte(mie, viewer_id=socio.id)
        return MioPickleballResponse(
            profilo=self._profilo_response(prof),
            singolo=statistiche["singolo"],
            doppio=statistiche["doppio"],
            partite_questo_mese=sum(1 for p in giocate if p.data >= inizio_mese),
            serie_vittorie=serie,
            compagno_frequente=piu_frequente(compagni),
            avversario_frequente=piu_frequente(avversari),
            da_confermare=[r for r in risposte if r.da_confermare],
            in_attesa_altri=[
                r for r, p in zip(risposte, mie)
                if p.inserita_da == socio.id and p.stato in ("in_attesa_conferma", "contestata")
            ],
            recenti=[r for r in risposte if r.stato == "confermata"][:15],
        )

    async def cerca_giocatori(self, q: str, *, escludi: UUID | None = None) -> list[GiocatoreRicerca]:
        termine = f"%{q.strip()}%"
        r = await self.db.execute(
            select(Socio)
            .where(
                Socio.is_minor.is_(False),
                (func.concat(Socio.nome, " ", Socio.cognome).ilike(termine))
                | (func.concat(Socio.cognome, " ", Socio.nome).ilike(termine)),
            )
            .order_by(Socio.cognome, Socio.nome)
            .limit(10)
        )
        soci = [s for s in r.scalars().all() if s.id != escludi]
        ratings = defaultdict(dict)
        if soci:
            for rp in (
                await self.db.execute(select(RatingPickleball).where(RatingPickleball.socio_id.in_([s.id for s in soci])))
            ).scalars().all():
                ratings[rp.socio_id][rp.formato] = float(rp.rating)
        return [
            GiocatoreRicerca(
                socio_id=s.id, nome=nome_breve(s),
                rating_singolo=ratings[s.id].get("singolo"), rating_doppio=ratings[s.id].get("doppio"),
            )
            for s in soci
        ]

    # ─── dirigenza ──────────────────────────────────────────────────────────

    async def registra_dirigenza(self, operatore_id: UUID | None, dati: PartitaDirigenzaCreate) -> PartitaResponse:
        ospiti = await self._verifica_giocatori(list(dati.squadra_a) + list(dati.squadra_b), ammetti_ospiti=True)
        p = await self.crea_partita(
            formato=dati.formato, data=dati.data, squadra_a=list(dati.squadra_a), squadra_b=list(dati.squadra_b),
            punteggi=dati.punteggi, confermata=True, inserita_da=operatore_id, dirigenza=True, ospiti=ospiti,
            torneo=dati.torneo, note=dati.note,
        )
        await self.db.refresh(p)
        return (await self.risposte([p], nomi_completi=True))[0]

    async def risolvi(self, partita_id: UUID, esito: str, operatore_id: UUID | None) -> None:
        p = await self._partita_per_update(partita_id)
        era_confermata = p.stato == "confermata"
        if esito == "conferma":
            if p.stato not in ("in_attesa_conferma", "contestata"):
                raise HTTPException(status.HTTP_409_CONFLICT, detail="La partita non è da confermare")
            p.stato = "confermata"
            p.confermata_da = operatore_id
            p.confermata_at = datetime.now(timezone.utc)
        else:
            if p.stato == "annullata":
                return
            p.stato = "annullata"
        await self.db.flush()
        if esito == "conferma" or era_confermata:
            await self.ricalcola(p.formato)
            if p.torneo_id:
                from modules.pickleball.tornei import TorneiService
                await TorneiService(self.db).calcola_piazzamenti(p.torneo_id)

    async def lista_dirigenza(self, stato: str | None = None, limite: int = 200) -> list[PartitaResponse]:
        q = select(PartitaPickleball).order_by(PartitaPickleball.data.desc(), PartitaPickleball.created_at.desc())
        if stato:
            q = q.where(PartitaPickleball.stato == stato)
        partite = (await self.db.execute(q.limit(limite))).scalars().all()
        return await self.risposte(list(partite), nomi_completi=True)

    async def cerca_giocatori_dirigenza(self, q: str) -> list[GiocatoreRicerca]:
        termine = f"%{q.strip()}%"
        r = await self.db.execute(
            select(Socio)
            .where(
                (func.concat(Socio.nome, " ", Socio.cognome).ilike(termine))
                | (func.concat(Socio.cognome, " ", Socio.nome).ilike(termine))
                | Socio.codice_fiscale.ilike(termine)
            )
            .order_by(Socio.cognome, Socio.nome)
            .limit(10)
        )
        out = [
            GiocatoreRicerca(socio_id=s.id, nome=f"{s.nome} {s.cognome}", rating_singolo=None, rating_doppio=None)
            for s in r.scalars().all()
        ]
        r = await self.db.execute(
            select(GiocatoreOspite)
            .where(
                (func.concat(GiocatoreOspite.nome, " ", GiocatoreOspite.cognome).ilike(termine))
                | (func.concat(GiocatoreOspite.cognome, " ", GiocatoreOspite.nome).ilike(termine))
            )
            .order_by(GiocatoreOspite.cognome, GiocatoreOspite.nome)
            .limit(5)
        )
        out += [
            GiocatoreRicerca(socio_id=o.id, ospite=True, nome=nome_ospite(o, True), rating_singolo=None, rating_doppio=None)
            for o in r.scalars().all()
        ]
        return out

    async def dashboard_dirigenza(self) -> DashboardPickleballDirigenza:
        oggi = date.today()
        da_30 = oggi - timedelta(days=30)
        conta = lambda *cond: select(func.count()).select_from(PartitaPickleball).where(*cond)
        partite_30 = (await self.db.execute(
            conta(PartitaPickleball.stato == "confermata", PartitaPickleball.data >= da_30))).scalar_one()
        totali = (await self.db.execute(conta(PartitaPickleball.stato == "confermata"))).scalar_one()
        contestate = (await self.db.execute(conta(PartitaPickleball.stato == "contestata"))).scalar_one()
        in_attesa = (await self.db.execute(conta(PartitaPickleball.stato == "in_attesa_conferma"))).scalar_one()
        attivi = (await self.db.execute(
            select(func.count(func.distinct(GiocatorePartita.socio_id)))
            .join(PartitaPickleball, PartitaPickleball.id == GiocatorePartita.partita_id)
            .where(PartitaPickleball.stato == "confermata", PartitaPickleball.data >= da_30)
        )).scalar_one()

        inizio = oggi - timedelta(days=oggi.weekday()) - timedelta(weeks=7)
        settimana = func.date_trunc("week", PartitaPickleball.data)
        per_sett = {d.date() if hasattr(d, "date") else d: n for d, n in (await self.db.execute(
            select(settimana, func.count())
            .where(PartitaPickleball.stato == "confermata", PartitaPickleball.data >= inizio)
            .group_by(settimana)
        )).all()}
        return DashboardPickleballDirigenza(
            giocatori_attivi_30gg=attivi, partite_30gg=partite_30, partite_totali=totali,
            da_risolvere=contestate, in_attesa_conferma=in_attesa,
            per_settimana=[
                SettimanaPartite(settimana=inizio + timedelta(weeks=i), partite=per_sett.get(inizio + timedelta(weeks=i), 0))
                for i in range(8)
            ],
            top_singolo=await self.classifica("singolo", completa=True, limite=5),
            top_doppio=await self.classifica("doppio", completa=True, limite=5),
        )
