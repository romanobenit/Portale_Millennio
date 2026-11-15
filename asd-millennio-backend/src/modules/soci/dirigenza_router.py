from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import RequireDirigenza
from modules.soci.gestione_tesseramenti import GestioneTesseramentiService
from schemas.tesseramento import ModificaTesseramentoRequest, TesseramentoDettaglioResponse

router = APIRouter(prefix="/dirigenza/tesseramenti", tags=["Dirigenza — Tesseramenti"])


@router.get("/{tessera_id}", response_model=TesseramentoDettaglioResponse)
async def dettaglio_tesseramento(
    tessera_id: UUID, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")
):
    return await GestioneTesseramentiService(db).dettaglio(tessera_id)


@router.patch("/{tessera_id}", response_model=TesseramentoDettaglioResponse)
async def modifica_tesseramento(
    tessera_id: UUID,
    data: ModificaTesseramentoRequest,
    _=RequireDirigenza,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Corregge la tessera e/o l'anagrafica del socio (solo i campi inviati)."""
    return await GestioneTesseramentiService(db).modifica(tessera_id, data)


@router.delete("/{tessera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def elimina_tesseramento(
    tessera_id: UUID, _=RequireDirigenza, db: AsyncSession = Depends(get_db, scope="function")
):
    """Elimina una tessera inserita per errore, se non ha pagamenti online registrati."""
    await GestioneTesseramentiService(db).elimina(tessera_id)
