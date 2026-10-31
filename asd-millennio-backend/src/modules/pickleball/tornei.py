"""
Tornei di pickleball, giocatori ospiti, circuito stagionale e impostazioni.

- Le partite di un torneo sono inserite dalla dirigenza (anche da file) e contano subito.
- I piazzamenti di ogni categoria sono ricavati dalle partite; la dirigenza può correggerli
  (le correzioni manuali non vengono toccate dai ricalcoli).
- Il circuito somma i punti dei migliori N piazzamenti di una stagione, per categoria.
- Gli ospiti (non soci) servono all'Elo dei soci, non compaiono in classifica e possono
  essere invitati a iscriversi alla community; quando si iscrivono si collegano al socio.
"""
import html
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import logger
from models.pickleball import (
    ConfigPickleball,
    GiocatoreOspite,
    GiocatorePartita,
    PartitaPickleball,
    PiazzamentoTorneo,
    ProfiloAtleta,
    RatingOspite,
    TorneoPickleball,
)
from models.socio import Socio
from modules.eventi.email import _invia, _layout
from modules.pickleball import import_risultati
from modules.pickleball.import_risultati import normalizza_nome
from modules.pickleball.regole import (
    anno_sportivo_di,
    migliore,
    piazzamenti_categoria,
    punti_piazzamento,
)
from modules.pickleball.service import FORMATI, PickleballService
from schemas.pickleball import (
    CircuitoResponse,
    ConfigPickleballSchema,
    GiocatoreImport,
    ImportRisultatiResponse,
    OspiteCreate,
    OspiteResponse,
    OspiteUpdate,
    PiazzamentoResponse,
    PiazzamentoUpdate,
    RigaCircuito,
    RigaImportRisultato,
    RisultatoCircuito,
    TorneoCreate,
    TorneoDettaglioResponse,
    TorneoResponse,
    TorneoUpdate,
)

settings = get_settings()


class TorneiService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pb = PickleballService(db)

    # ─── impostazioni ───────────────────────────────────────────────────────

    async def leggi_config(self) -> ConfigPickleballSchema:
        return ConfigPickleballSchema(**await self.pb.config())

    async def salva_config(self, dati: ConfigPickleballSchema) -> ConfigPickleballSchema:
        riga = (await self.db.execute(select(ConfigPickleball).where(ConfigPickleball.id == 1))).scalar_one_or_none()
        if riga is None:
            riga = ConfigPickleball(id=1, valori={})
            self.db.add(riga)
        riga.valori = dati.model_dump()
        await self.db.flush()
        for formato in FORMATI:
            await self.pb.ricalcola(formato)
        logger.info("Impostazioni pickleball aggiornate")
        return await self.leggi_config()

    # ─── tornei ─────────────────────────────────────────────────────────────

    async def _torneo(self, torneo_id: UUID) -> TorneoPickleball:
        t = (await self.db.execute(select(TorneoPickleball).where(TorneoPickleball.id == torneo_id))).scalar_one_or_none()
        if not t:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Torneo non trovato")
        return t

    async def _torneo_response(self, t: TorneoPickleball) -> TorneoResponse:
        r = await self.db.execute(
            select(PartitaPickleball.categoria, func.count())
            .where(PartitaPickleball.torneo_id == t.id, PartitaPickleball.stato != "annullata")
            .group_by(PartitaPickleball.categoria)
        )
        per_cat = dict(r.all())
        return TorneoResponse(
            id=t.id, nome=t.nome, data=t.data, luogo=t.luogo, livello=t.livello, anno_sportivo=t.anno_sportivo,
            concluso=t.concluso, url_esterno=t.url_esterno, note=t.note,
            partite=sum(per_cat.values()), categorie=sorted(c for c in per_cat if c),
        )

    async def lista(self) -> list[TorneoResponse]:
        tornei = (await self.db.execute(
            select(TorneoPickleball).order_by(TorneoPickleball.data.desc())
        )).scalars().all()
        return [await self._torneo_response(t) for t in tornei]

    async def crea(self, dati: TorneoCreate) -> TorneoResponse:
        t = TorneoPickleball(**dati.model_dump(), anno_sportivo=anno_sportivo_di(dati.data), concluso=False)
        self.db.add(t)
        await self.db.flush()
        logger.info("Torneo pickleball creato: %s (%s)", t.id, t.data)
        return await self._torneo_response(t)

    async def aggiorna(self, torneo_id: UUID, dati: TorneoUpdate) -> TorneoResponse:
        t = await self._torneo(torneo_id)
        valori = dati.model_dump(exclude_unset=True)
        ricalcola = "data" in valori or "livello" in valori
        for campo, valore in valori.items():
            if valore is None and campo in ("nome", "data", "livello", "concluso"):
                continue
            setattr(t, campo, valore)
        t.anno_sportivo = anno_sportivo_di(t.data)
        if valori.get("data"):
            await self.db.execute(
                PartitaPickleball.__table__.update()
                .where(PartitaPickleball.torneo_id == t.id)
                .values(data=t.data)
            )
        await self.db.flush()
        if ricalcola:
            for formato in FORMATI:
                await self.pb.ricalcola(formato)
        if valori.get("concluso"):
            await self.calcola_piazzamenti(t.id)
        return await self._torneo_response(t)

    async def elimina(self, torneo_id: UUID) -> None:
        t = await self._torneo(torneo_id)
        await self.db.delete(t)          # partite e piazzamenti in cascata
        await self.db.flush()
        for formato in FORMATI:
            await self.pb.ricalcola(formato)
        logger.info("Torneo pickleball eliminato: %s", torneo_id)

    async def dettaglio(self, torneo_id: UUID) -> TorneoDettaglioResponse:
        t = await self._torneo(torneo_id)
        partite = (await self.db.execute(
            select(PartitaPickleball)
            .where(PartitaPickleball.torneo_id == t.id)
            .order_by(PartitaPickleball.categoria, PartitaPickleball.created_at)
        )).scalars().all()
        return TorneoDettaglioResponse(
            torneo=await self._torneo_response(t),
            partite=await self.pb.risposte(list(partite), nomi_completi=True),
            piazzamenti=await self._piazzamenti(t),
        )

    async def _piazzamenti(self, t: TorneoPickleball) -> list[PiazzamentoResponse]:
        cfg = await self.pb.config()
        righe = (await self.db.execute(
            select(PiazzamentoTorneo).where(PiazzamentoTorneo.torneo_id == t.id)
        )).scalars().all()
        nomi = await self.pb.nomi([r.socio_id for r in righe], [r.ospite_id for r in righe], completi=True)
        ordine = {"vincitore": 0, "finalista": 1, "semifinalista": 2, "fase_finale": 3, "partecipazione": 4, "nessuno": 5}
        return sorted(
            (
                PiazzamentoResponse(
                    giocatore_id=r.giocatore_id, nome=nomi.get(r.giocatore_id, "—"), ospite=r.ospite_id is not None,
                    categoria=r.categoria, piazzamento=r.piazzamento, manuale=r.manuale,
                    punti=punti_piazzamento(r.piazzamento, t.livello, cfg),
                )
                for r in righe
            ),
            key=lambda p: (p.categoria, ordine[p.piazzamento], p.nome),
        )

    async def calcola_piazzamenti(self, torneo_id: UUID) -> None:
        """Ricava i piazzamenti dalle partite; le correzioni manuali restano."""
        partite = (await self.db.execute(
            select(PartitaPickleball).where(
                PartitaPickleball.torneo_id == torneo_id,
                PartitaPickleball.stato == "confermata",
                PartitaPickleball.categoria.isnot(None),
            )
        )).scalars().all()
        gioc = await self.pb._giocatori([p.id for p in partite])
        ospiti = {g.ospite_id for lst in gioc.values() for g in lst if g.ospite_id}
        per_cat: dict = defaultdict(list)
        for p in partite:
            lst = gioc[p.id]
            per_cat[p.categoria].append({
                "fase": p.fase, "vincitore": p.vincitore, "walkover": p.walkover, "punteggi": p.punteggi,
                "a": [g.giocatore_id for g in lst if g.squadra == "a"],
                "b": [g.giocatore_id for g in lst if g.squadra == "b"],
            })
        manuali = (await self.db.execute(
            select(PiazzamentoTorneo).where(PiazzamentoTorneo.torneo_id == torneo_id, PiazzamentoTorneo.manuale.is_(True))
        )).scalars().all()
        fissati = {(m.categoria, m.giocatore_id) for m in manuali}
        await self.db.execute(delete(PiazzamentoTorneo).where(
            PiazzamentoTorneo.torneo_id == torneo_id, PiazzamentoTorneo.manuale.is_(False)
        ))
        for categoria, lista in per_cat.items():
            for gid, piazzamento in piazzamenti_categoria(lista).items():
                if (categoria, gid) in fissati:
                    continue
                self.db.add(PiazzamentoTorneo(
                    torneo_id=torneo_id, categoria=categoria, piazzamento=piazzamento,
                    socio_id=None if gid in ospiti else gid, ospite_id=gid if gid in ospiti else None,
                ))
        await self.db.flush()

    async def imposta_piazzamento(self, torneo_id: UUID, dati: PiazzamentoUpdate) -> list[PiazzamentoResponse]:
        t = await self._torneo(torneo_id)
        categoria = dati.categoria.upper()
        ospite = (await self.pb._ospiti([dati.giocatore_id])).get(dati.giocatore_id)
        if not ospite and not await self.pb._soci([dati.giocatore_id]):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Giocatore non trovato")
        colonna = PiazzamentoTorneo.ospite_id if ospite else PiazzamentoTorneo.socio_id
        riga = (await self.db.execute(select(PiazzamentoTorneo).where(
            PiazzamentoTorneo.torneo_id == t.id, PiazzamentoTorneo.categoria == categoria, colonna == dati.giocatore_id,
        ))).scalar_one_or_none()
        if riga is None:
            riga = PiazzamentoTorneo(
                torneo_id=t.id, categoria=categoria,
                socio_id=None if ospite else dati.giocatore_id, ospite_id=dati.giocatore_id if ospite else None,
                piazzamento=dati.piazzamento,
            )
            self.db.add(riga)
        riga.piazzamento = dati.piazzamento
        riga.manuale = True
        await self.db.flush()
        return await self._piazzamenti(t)

    # ─── importazione risultati ─────────────────────────────────────────────

    async def _indice_nomi(self) -> tuple[dict, dict]:
        soci: dict = defaultdict(set)
        for s in (await self.db.execute(select(Socio.id, Socio.nome, Socio.cognome))).all():
            soci[normalizza_nome(f"{s.nome} {s.cognome}")].add(s.id)
            soci[normalizza_nome(f"{s.cognome} {s.nome}")].add(s.id)
        ospiti: dict = defaultdict(set)
        for o in (await self.db.execute(select(GiocatoreOspite.id, GiocatoreOspite.nome, GiocatoreOspite.cognome))).all():
            ospiti[normalizza_nome(f"{o.nome} {o.cognome}")].add(o.id)
            ospiti[normalizza_nome(f"{o.cognome} {o.nome}")].add(o.id)
        return soci, ospiti

    async def importa(
        self, torneo_id: UUID, content: bytes, conferma: bool, operatore_id: UUID | None
    ) -> ImportRisultatiResponse:
        t = await self._torneo(torneo_id)
        try:
            righe = import_risultati.leggi_file(content)
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        idx_soci, idx_ospiti = await self._indice_nomi()
        nuovi: dict[str, str] = {}        # nome normalizzato -> nome come scritto nel file

        def risolvi(nome: str) -> tuple[GiocatoreImport, object]:
            k = normalizza_nome(nome)
            if len(idx_soci.get(k, ())) > 1:
                raise ValueError(f"«{nome}»: più soci con questo nome, inserisci la partita a mano")
            if idx_soci.get(k):
                return GiocatoreImport(nome=nome, tipo="socio"), ("socio", next(iter(idx_soci[k])))
            if idx_ospiti.get(k):
                return GiocatoreImport(nome=nome, tipo="ospite"), ("ospite", next(iter(idx_ospiti[k])))
            nuovi.setdefault(k, nome)
            return GiocatoreImport(nome=nome, tipo="nuovo_ospite"), ("nuovo", k)

        # firme delle partite già presenti nel torneo, per non importare due volte lo stesso file
        esistenti = (await self.db.execute(
            select(PartitaPickleball).where(PartitaPickleball.torneo_id == t.id, PartitaPickleball.stato != "annullata")
        )).scalars().all()
        gioc = await self.pb._giocatori([p.id for p in esistenti])
        firme = {
            (p.categoria, p.fase, tuple(sorted(str(g.giocatore_id) for g in gioc[p.id] if g.squadra == "a")),
             tuple(sorted(str(g.giocatore_id) for g in gioc[p.id] if g.squadra == "b")))
            for p in esistenti
        }

        out: list[RigaImportRisultato] = []
        da_creare: list[tuple] = []
        for r in righe:
            esito, messaggio = "ok", None
            sq_a, sq_b, ref_a, ref_b = [], [], [], []
            try:
                for nome in r.squadra_a:
                    gi, ref = risolvi(nome)
                    sq_a.append(gi)
                    ref_a.append(ref)
                for nome in r.squadra_b:
                    gi, ref = risolvi(nome)
                    sq_b.append(gi)
                    ref_b.append(ref)
            except ValueError as e:
                esito, messaggio = "errore", str(e)
            if esito == "ok":
                if r.errore:
                    esito, messaggio = "errore", r.errore
                elif r.saltata:
                    esito, messaggio = "saltata", r.saltata
                elif len(set(ref_a + ref_b)) != len(ref_a + ref_b):
                    esito, messaggio = "errore", "lo stesso giocatore compare due volte"
                elif all(x[0] != "nuovo" for x in ref_a + ref_b) and (
                    r.categoria, r.fase,
                    tuple(sorted(str(x[1]) for x in ref_a)), tuple(sorted(str(x[1]) for x in ref_b)),
                ) in firme:
                    esito, messaggio = "gia_importata", "già presente nel torneo"
            punteggio = "WO" if r.walkover else ", ".join(f"{a}-{b}" for a, b in r.punteggi)
            out.append(RigaImportRisultato(
                riga=r.riga, categoria=r.categoria, fase=r.fase, squadra_a=sq_a, squadra_b=sq_b,
                punteggio=punteggio, vincitore=r.vincitore.upper() if r.vincitore else None,
                walkover=r.walkover, esito=esito, messaggio=messaggio,
            ))
            if esito == "ok":
                da_creare.append((r, ref_a, ref_b))

        nuovi_usati = sorted({
            nuovi[x[1]] for _, ra, rb in da_creare for x in ra + rb if x[0] == "nuovo"
        })
        risposta = ImportRisultatiResponse(
            righe=out,
            da_importare=len(da_creare),
            errori=sum(1 for x in out if x.esito == "errore"),
            saltate=sum(1 for x in out if x.esito == "saltata"),
            gia_importate=sum(1 for x in out if x.esito == "gia_importata"),
            nuovi_ospiti=nuovi_usati,
        )
        if not conferma or not da_creare:
            return risposta

        creati: dict[str, UUID] = {}
        for k in {x[1] for _, ra, rb in da_creare for x in ra + rb if x[0] == "nuovo"}:
            parti = nuovi[k].split()
            o = GiocatoreOspite(nome=parti[0], cognome=" ".join(parti[1:]) or "—")
            self.db.add(o)
            await self.db.flush()
            creati[k] = o.id

        def ids(refs) -> tuple[list[UUID], set[UUID]]:
            lista, ospiti = [], set()
            for tipo, v in refs:
                gid = creati[v] if tipo == "nuovo" else v
                lista.append(gid)
                if tipo != "socio":
                    ospiti.add(gid)
            return lista, ospiti

        formati = set()
        for r, ref_a, ref_b in da_creare:
            a, osp_a = ids(ref_a)
            b, osp_b = ids(ref_b)
            formato = "doppio" if max(len(a), len(b)) == 2 else "singolo"
            formati.add(formato)
            await self.pb.crea_partita(
                formato=formato, data=t.data, squadra_a=a, squadra_b=b, punteggi=r.punteggi,
                confermata=True, inserita_da=operatore_id, dirigenza=True, ospiti=osp_a | osp_b,
                torneo_id=t.id, categoria=r.categoria, fase=r.fase, walkover=r.walkover,
                vincitore=r.vincitore, ricalcola=False,
            )
        for formato in formati:
            await self.pb.ricalcola(formato)
        await self.calcola_piazzamenti(t.id)
        risposta.importate = len(da_creare)
        logger.info("Torneo %s: importate %d partite, %d nuovi ospiti", t.id, len(da_creare), len(creati))
        return risposta

    # ─── circuito ───────────────────────────────────────────────────────────

    async def circuito(
        self, anno: str | None, categoria: str | None, *, completo: bool
    ) -> CircuitoResponse:
        cfg = await self.pb.config()
        anni = sorted(
            {a for (a,) in (await self.db.execute(
                select(TorneoPickleball.anno_sportivo).where(TorneoPickleball.concluso.is_(True)).distinct()
            )).all()},
            reverse=True,
        )
        anno = anno or (anni[0] if anni else None)
        tornei = {t.id: t for t in (await self.db.execute(
            select(TorneoPickleball).where(TorneoPickleball.anno_sportivo == anno, TorneoPickleball.concluso.is_(True))
        )).scalars().all()} if anno else {}
        piazz = (await self.db.execute(
            select(PiazzamentoTorneo).where(PiazzamentoTorneo.torneo_id.in_(list(tornei)))
        )).scalars().all() if tornei else []
        categorie = sorted({p.categoria for p in piazz})
        categoria = (categoria or "").upper() or (categorie[0] if categorie else None)
        piazz = [p for p in piazz if p.categoria == categoria and p.piazzamento != "nessuno"]

        soci = await self.pb._soci([p.socio_id for p in piazz])
        nascosti = set()
        if not completo:
            nascosti = {sid for sid, s in soci.items() if s.is_minor}
            r = await self.db.execute(select(ProfiloAtleta.socio_id).where(
                ProfiloAtleta.socio_id.in_(list(soci)), ProfiloAtleta.visibile_in_classifica.is_(False)
            ))
            nascosti |= set(r.scalars().all())
        nomi = await self.pb.nomi(
            [p.socio_id for p in piazz], [p.ospite_id for p in piazz] if completo else [], completi=completo
        )

        per_giocatore: dict = defaultdict(list)
        for p in piazz:
            if p.ospite_id and not completo:
                continue
            if p.socio_id in nascosti:
                continue
            t = tornei[p.torneo_id]
            per_giocatore[p.giocatore_id].append(RisultatoCircuito(
                torneo_id=t.id, torneo=t.nome, data=t.data, piazzamento=p.piazzamento,
                punti=punti_piazzamento(p.piazzamento, t.livello, cfg), conta=False,
            ))
        righe = []
        for gid, risultati in per_giocatore.items():
            migliori = sorted(risultati, key=lambda x: x.punti, reverse=True)[: cfg["migliori_risultati"]]
            for x in migliori:
                x.conta = True
            righe.append(RigaCircuito(
                posizione=0, giocatore_id=gid, nome=nomi.get(gid, "—"), ospite=gid not in soci,
                punti=round(sum(x.punti for x in migliori), 1), tornei=len(risultati),
                risultati=sorted(risultati, key=lambda x: x.data),
            ))
        righe.sort(key=lambda r: (-r.punti, r.nome))
        for i, r in enumerate(righe, start=1):
            r.posizione = i
        return CircuitoResponse(
            anno_sportivo=anno, categoria=categoria, anni=anni, categorie=categorie,
            migliori_risultati=cfg["migliori_risultati"], righe=righe,
        )

    # ─── ospiti ─────────────────────────────────────────────────────────────

    async def _ospite(self, ospite_id: UUID) -> GiocatoreOspite:
        o = (await self.db.execute(select(GiocatoreOspite).where(GiocatoreOspite.id == ospite_id))).scalar_one_or_none()
        if not o:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ospite non trovato")
        return o

    async def _ospiti_response(self, ospiti: list[GiocatoreOspite]) -> list[OspiteResponse]:
        ids = [o.id for o in ospiti]
        partite = dict((await self.db.execute(
            select(GiocatorePartita.ospite_id, func.count()).where(GiocatorePartita.ospite_id.in_(ids))
            .group_by(GiocatorePartita.ospite_id)
        )).all()) if ids else {}
        rating: dict = defaultdict(dict)
        if ids:
            for r in (await self.db.execute(select(RatingOspite).where(RatingOspite.ospite_id.in_(ids)))).scalars():
                rating[r.ospite_id][r.formato] = float(r.rating)
        return [
            OspiteResponse(
                id=o.id, nome=o.nome, cognome=o.cognome, club=o.club, email=o.email, sesso=o.sesso,
                anno_nascita=o.anno_nascita, invitato_at=o.invitato_at, partite=partite.get(o.id, 0),
                rating_singolo=rating[o.id].get("singolo"), rating_doppio=rating[o.id].get("doppio"),
            )
            for o in ospiti
        ]

    async def lista_ospiti(self) -> list[OspiteResponse]:
        ospiti = (await self.db.execute(
            select(GiocatoreOspite).order_by(GiocatoreOspite.cognome, GiocatoreOspite.nome)
        )).scalars().all()
        return await self._ospiti_response(list(ospiti))

    async def crea_ospite(self, dati: OspiteCreate) -> OspiteResponse:
        o = GiocatoreOspite(**dati.model_dump())
        self.db.add(o)
        await self.db.flush()
        return (await self._ospiti_response([o]))[0]

    async def aggiorna_ospite(self, ospite_id: UUID, dati: OspiteUpdate) -> OspiteResponse:
        o = await self._ospite(ospite_id)
        for campo, valore in dati.model_dump(exclude_unset=True).items():
            if valore is None and campo in ("nome", "cognome"):
                continue
            setattr(o, campo, valore)
        await self.db.flush()
        return (await self._ospiti_response([o]))[0]

    async def invita_ospite(self, ospite_id: UUID) -> OspiteResponse:
        o = await self._ospite(ospite_id)
        if not o.email:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Manca l'email: aggiungila solo se il giocatore ha accettato di essere contattato.",
            )
        corpo = (
            f'<p style="line-height:1.6">Ciao {html.escape(o.nome)},<br>'
            "ti abbiamo incontrato sui campi di pickleball e ci farebbe piacere averti nella "
            "<strong>community dell'ASD Millennio</strong>.</p>"
            '<p style="line-height:1.6">Se hai già la tessera di un\'altra ASD puoi iscriverti alla community '
            "senza tesserarti con noi: potrai prenotare gli eventi al Palasirio e comparire nella classifica "
            "del club, con i risultati dei tornei a cui hai già partecipato.</p>"
            f'<p style="line-height:1.6"><a href="{html.escape(settings.app_url)}/dashboard/onboarding" '
            'style="color:#1d4ed8;font-weight:bold">Iscriviti alla community</a></p>'
            '<p style="line-height:1.6;color:#6b7280;font-size:13px">Ricevi questa email una sola volta perché '
            "l'hai lasciata alla dirigenza durante un torneo. Se non ti interessa, ignorala.</p>"
        )
        inviata = await _invia(o.email, "Unisciti alla community dell'ASD Millennio", _layout("Ti aspettiamo!", corpo))
        if not inviata:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Invio dell'email non riuscito, riprova più tardi.")
        o.invitato_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("Invito community inviato all'ospite %s", o.id)
        return (await self._ospiti_response([o]))[0]

    async def collega_ospite(self, ospite_id: UUID, socio_id: UUID) -> None:
        """L'ospite si è iscritto: le sue partite e i suoi piazzamenti passano al socio, l'ospite sparisce."""
        o = await self._ospite(ospite_id)
        if not await self.pb._soci([socio_id]):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Socio non trovato")
        righe = (await self.db.execute(
            select(GiocatorePartita).where(GiocatorePartita.ospite_id == o.id)
        )).scalars().all()
        gia = set((await self.db.execute(select(GiocatorePartita.partita_id).where(
            GiocatorePartita.socio_id == socio_id, GiocatorePartita.partita_id.in_([g.partita_id for g in righe])
        ))).scalars().all()) if righe else set()
        if gia:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Il socio e l'ospite compaiono nella stessa partita: non possono essere la stessa persona.",
            )
        for g in righe:
            g.socio_id, g.ospite_id = socio_id, None
        piazz = (await self.db.execute(
            select(PiazzamentoTorneo).where(PiazzamentoTorneo.ospite_id == o.id)
        )).scalars().all()
        for p in piazz:
            esistente = (await self.db.execute(select(PiazzamentoTorneo).where(
                PiazzamentoTorneo.torneo_id == p.torneo_id, PiazzamentoTorneo.categoria == p.categoria,
                PiazzamentoTorneo.socio_id == socio_id,
            ))).scalar_one_or_none()
            if esistente:
                esistente.piazzamento = migliore(esistente.piazzamento, p.piazzamento)
                await self.db.delete(p)
            else:
                p.socio_id, p.ospite_id = socio_id, None
        await self.db.flush()
        await self.db.delete(o)
        await self.db.flush()
        for formato in FORMATI:
            await self.pb.ricalcola(formato)
        logger.info("Ospite %s collegato al socio %s", ospite_id, socio_id)

    async def elimina_ospite(self, ospite_id: UUID) -> None:
        o = await self._ospite(ospite_id)
        n = (await self.db.execute(
            select(func.count()).select_from(GiocatorePartita).where(GiocatorePartita.ospite_id == o.id)
        )).scalar_one()
        if n:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="L'ospite ha partite registrate: eliminale prima o collegalo a un socio.",
            )
        await self.db.delete(o)
        await self.db.flush()
