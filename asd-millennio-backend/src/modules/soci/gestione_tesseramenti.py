"""
Gestione dei tesseramenti da parte della dirigenza: correggere una tessera e
l'anagrafica del socio, oppure eliminare una tessera inserita per errore.

- Si elimina solo una tessera senza pagamenti online registrati (pagata, rimborsata
  o diventata erogazione liberale): quelle restano come prova contabile e si
  sospendono invece di cancellarle.
- Il socio resta anche senza tessere: per cancellarne i dati c'è la procedura GDPR.
- Nei log solo identificativi e nomi dei campi, mai i valori anagrafici.
"""
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from models.pagamento_tessera import PagamentoTessera
from models.socio import Socio
from models.tessera import Tessera
from modules.soci.codice_fiscale import cf_valido
from modules.soci.service import SPORT_PREFISSI, _genera_numero_tessera
from schemas.tesseramento import (
    ModificaTesseramentoRequest,
    PagamentoTesseraBreve,
    TesseramentoDettaglioResponse,
)

# La community richiede la tessera di un'altra ASD: non ci si entra né si esce cambiando categoria.
CATEGORIE_CAMBIABILI = set(SPORT_PREFISSI) - {"community"}
# Pagamenti che documentano un incasso (o un rimborso): la tessera non si elimina.
PAGAMENTI_CONTABILI = {"pagato", "rimborsato", "erogazione_liberale"}


def _eta(nascita: date, oggi: date | None = None) -> int:
    oggi = oggi or date.today()
    return oggi.year - nascita.year - ((oggi.month, oggi.day) < (nascita.month, nascita.day))


def pulisci_nome(valore: str) -> str:
    """Toglie spazi doppi e ai lati ("Michele  Vaccaro" → "Michele Vaccaro")."""
    return " ".join(valore.split())


def motivo_non_eliminabile(stati_pagamento: list[str]) -> str | None:
    if any(s in PAGAMENTI_CONTABILI for s in stati_pagamento):
        return (
            "La quota è stata pagata online: il pagamento resta registrato e la tessera non si può eliminare. "
            "Se non è più valida, sospendila."
        )
    return None


class GestioneTesseramentiService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _tessera(self, tessera_id: UUID) -> tuple[Tessera, Socio]:
        row = (
            await self.db.execute(
                select(Tessera, Socio)
                .join(Socio, Socio.id == Tessera.socio_id)
                .where(Tessera.id == tessera_id)
                .with_for_update(of=Tessera)
            )
        ).first()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tessera non trovata")
        return row[0], row[1]

    async def dettaglio(self, tessera_id: UUID) -> TesseramentoDettaglioResponse:
        t, s = await self._tessera(tessera_id)
        pagamenti = (
            await self.db.execute(
                select(PagamentoTessera)
                .where(PagamentoTessera.tessera_id == t.id)
                .order_by(PagamentoTessera.created_at)
            )
        ).scalars().all()
        altre = (
            await self.db.execute(
                select(func.count()).select_from(Tessera).where(Tessera.socio_id == s.id, Tessera.id != t.id)
            )
        ).scalar_one()
        motivo = motivo_non_eliminabile([p.stato for p in pagamenti])
        return TesseramentoDettaglioResponse(
            tessera_id=t.id,
            numero_tessera=t.numero_tessera,
            categoria=t.sport,
            stato=t.stato,
            anno_sportivo=t.anno_sportivo,
            data_emissione=t.data_emissione,
            data_scadenza=t.data_scadenza,
            verifica_stato=t.verifica_stato,
            certificato_medico_tipo=t.certificato_medico_tipo,
            certificato_medico_scadenza=t.certificato_medico_scadenza,
            socio_id=s.id,
            nome=s.nome,
            cognome=s.cognome,
            codice_fiscale=s.codice_fiscale,
            data_nascita=s.data_nascita,
            email=s.email,
            telefono=s.telefono,
            indirizzo=s.indirizzo,
            is_minor=s.is_minor,
            altre_tessere=altre,
            pagamenti=[
                PagamentoTesseraBreve(importo_eur=p.importo_eur, stato=p.stato, created_at=p.created_at)
                for p in pagamenti
            ],
            eliminabile=motivo is None,
            motivo_non_eliminabile=motivo,
        )

    async def modifica(self, tessera_id: UUID, data: ModificaTesseramentoRequest) -> TesseramentoDettaglioResponse:
        t, s = await self._tessera(tessera_id)
        campi: list[str] = []

        if data.tessera:
            d = data.tessera.model_dump(exclude_unset=True)
            if "categoria" in d and d["categoria"] != t.sport:
                await self._cambia_categoria(t, d.pop("categoria"))
                campi.append("categoria")
            d.pop("categoria", None)
            if "stato" in d and d["stato"] is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Indica lo stato della tessera")
            if "data_scadenza" in d:
                if t.sport == "community" and d["data_scadenza"] is not None:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="L'iscrizione community non scade: vale la scadenza della tessera dell'altra ASD.",
                    )
                if t.sport != "community" and d["data_scadenza"] is None:
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Indica la data di scadenza")
            # Certificato: tipo e scadenza vanno insieme (entrambi o nessuno).
            tipo = d.get("certificato_medico_tipo", t.certificato_medico_tipo)
            scad = d.get("certificato_medico_scadenza", t.certificato_medico_scadenza)
            if (tipo is None) != (scad is None):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Per il certificato medico servono sia il tipo sia la scadenza (o nessuno dei due).",
                )
            for campo, valore in d.items():
                if getattr(t, campo) != valore:
                    setattr(t, campo, valore)
                    campi.append(campo)

        if data.socio:
            campi += await self._modifica_socio(s, data.socio.model_dump(exclude_unset=True))

        await self.db.flush()
        if campi:
            logger.info("Dirigenza: tessera %s modificata (campi: %s)", t.id, ", ".join(sorted(set(campi))))
        return await self.dettaglio(t.id)

    async def _cambia_categoria(self, t: Tessera, nuova: str | None) -> None:
        if nuova not in CATEGORIE_CAMBIABILI or t.sport not in CATEGORIE_CAMBIABILI:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Categoria non modificabile: l'iscrizione community si gestisce a parte.",
            )
        doppia = (
            await self.db.execute(
                select(Tessera.id).where(
                    Tessera.socio_id == t.socio_id,
                    Tessera.sport == nuova,
                    Tessera.anno_sportivo == t.anno_sportivo,
                    Tessera.id != t.id,
                    Tessera.stato.in_(["in_attesa_pagamento", "attiva"]),
                )
            )
        ).scalars().first()
        if doppia:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail=f"Il socio ha già una tessera {nuova} per il {t.anno_sportivo}."
            )
        t.numero_tessera = await _genera_numero_tessera(self.db, nuova, t.anno_sportivo)
        t.sport = nuova

    async def _modifica_socio(self, s: Socio, d: dict) -> list[str]:
        campi: list[str] = []
        for campo in ("nome", "cognome"):
            if campo in d:
                if not d[campo] or not d[campo].strip():
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Il campo {campo} è obbligatorio")
                d[campo] = pulisci_nome(d[campo])
        if "codice_fiscale" in d:
            cf = (d["codice_fiscale"] or "").upper().strip()
            if not cf_valido(cf):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Codice fiscale non valido (carattere di controllo errato).",
                )
            altro = (
                await self.db.execute(select(Socio.id).where(Socio.codice_fiscale == cf, Socio.id != s.id))
            ).scalar_one_or_none()
            if altro:
                raise HTTPException(status.HTTP_409_CONFLICT, detail="Codice fiscale già registrato per un altro socio.")
            d["codice_fiscale"] = cf
        if "data_nascita" in d:
            if d["data_nascita"] is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Indica la data di nascita")
            if d["data_nascita"] != s.data_nascita:
                if s.is_minor:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="La data di nascita di un minore la corregge il tutore dalla sua area.",
                    )
                if _eta(d["data_nascita"]) < 18:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Con questa data il socio risulterebbe minorenne: i minori vanno aggiunti dal tutore.",
                    )
        for campo in ("telefono", "indirizzo"):
            if campo in d:
                d[campo] = (d[campo] or "").strip() or None
        for campo, valore in d.items():
            if getattr(s, campo) != valore:
                setattr(s, campo, valore)
                campi.append(campo)
        return campi

    async def elimina(self, tessera_id: UUID) -> None:
        t, _ = await self._tessera(tessera_id)
        stati = list(
            (
                await self.db.execute(select(PagamentoTessera.stato).where(PagamentoTessera.tessera_id == t.id))
            ).scalars().all()
        )
        motivo = motivo_non_eliminabile(stati)
        if motivo:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=motivo)
        # Pagamenti mai completati (checkout abbandonati): spariscono con la tessera.
        await self.db.execute(delete(PagamentoTessera).where(PagamentoTessera.tessera_id == t.id))
        await self.db.delete(t)
        await self.db.flush()
        logger.info("Dirigenza: tessera %s (%s) eliminata", tessera_id, t.numero_tessera)
