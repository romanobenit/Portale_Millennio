"""
Regression: un socio con PIÙ tessere attive insieme (sport + sostenitore,
CLAUDE.md §M01) non deve far esplodere _verifica_tessera.

Bug riprodotto in UAT (2026-07-11): _verifica_tessera usava scalar_one_or_none()
sulla query "tessere attive del socio" — con due righe attive contemporaneamente
(introdotte dalla feature "socio sostenitore") solleva MultipleResultsFound,
il router lo propaga come 500 e il frontend lo mostra come "Errore di rete".
"""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import MultipleResultsFound


def _db_con_tessere(tessere: list) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = tessere[0] if tessere else None
    # Se il codice regredisse a scalar_one_or_none(), qui esploderebbe come nel
    # bug reale (SQLAlchemy la solleva davvero con >1 riga) — cattura il ritorno.
    if len(tessere) > 1:
        result.scalar_one_or_none.side_effect = MultipleResultsFound(
            "Multiple rows were found when one or none was required"
        )
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_verifica_tessera_con_due_tessere_attive_non_esplode():
    """Sport + sostenitore attive insieme: niente MultipleResultsFound."""
    from modules.campi.service import CampiService

    socio_id = uuid4()
    tessera_sport = MagicMock()
    tessera_sos = MagicMock()

    db = _db_con_tessere([tessera_sport, tessera_sos])
    # non deve sollevare alcuna eccezione
    await CampiService(db)._verifica_tessera(socio_id)


@pytest.mark.asyncio
async def test_verifica_tessera_senza_tessere_attive_403():
    from fastapi import HTTPException
    from modules.campi.service import CampiService

    socio_id = uuid4()
    db = _db_con_tessere([])

    with pytest.raises(HTTPException) as exc_info:
        await CampiService(db)._verifica_tessera(socio_id)

    assert exc_info.value.status_code == 403
