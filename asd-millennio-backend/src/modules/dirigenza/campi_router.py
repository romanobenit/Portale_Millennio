from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import RequireDirigenza
from models.slot_template_campo import SlotTemplateCampo
from schemas.campi import (
    SlotTemplateCampoCreate,
    SlotTemplateCampoResponse,
    SlotTemplateCampoUpdate,
)

router = APIRouter(prefix="/dirigenza/campi", tags=["Dirigenza — Campi"])


@router.get("/templates", response_model=List[SlotTemplateCampoResponse])
async def lista_templates(
    db: AsyncSession = Depends(get_db),
    _=RequireDirigenza,
):
    r = await db.execute(select(SlotTemplateCampo).order_by(SlotTemplateCampo.giorno_settimana))
    return [SlotTemplateCampoResponse.model_validate(t) for t in r.scalars().all()]


@router.post("/templates", response_model=SlotTemplateCampoResponse, status_code=status.HTTP_201_CREATED)
async def crea_template(
    body: SlotTemplateCampoCreate,
    db: AsyncSession = Depends(get_db),
    _=RequireDirigenza,
):
    if body.ora_fine <= body.ora_inizio:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ora_fine deve essere successiva a ora_inizio")
    if body.valido_fino_al < body.valido_dal:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="valido_fino_al deve essere successivo a valido_dal")

    tmpl = SlotTemplateCampo(**body.model_dump())
    db.add(tmpl)
    await db.flush()
    await db.refresh(tmpl)
    return SlotTemplateCampoResponse.model_validate(tmpl)


@router.put("/templates/{template_id}", response_model=SlotTemplateCampoResponse)
async def aggiorna_template(
    template_id: UUID,
    body: SlotTemplateCampoUpdate,
    db: AsyncSession = Depends(get_db),
    _=RequireDirigenza,
):
    r = await db.execute(select(SlotTemplateCampo).where(SlotTemplateCampo.id == template_id))
    tmpl = r.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template non trovato")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, value)

    await db.flush()
    await db.refresh(tmpl)
    return SlotTemplateCampoResponse.model_validate(tmpl)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disattiva_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    _=RequireDirigenza,
):
    r = await db.execute(select(SlotTemplateCampo).where(SlotTemplateCampo.id == template_id))
    tmpl = r.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template non trovato")
    tmpl.attivo = False
    await db.flush()
