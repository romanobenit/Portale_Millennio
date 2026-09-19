"""Indice unico parziale: una sola tessera attiva/in attesa per socio+sport+anno

Il controllo "esiste già una tessera per questa categoria e anno sportivo" in
avvia_tesseramento() era solo applicativo (SELECT prima di INSERT, senza lock):
due richieste concorrenti (doppio click, due tab) potevano superarlo entrambe e
creare due tessere/due sessioni Stripe per lo stesso socio+sport+anno.

Un vincolo UNIQUE pieno su (socio_id, sport, anno_sportivo) non va bene perché
bloccherebbe anche il re-tesseramento legittimo dopo una tessera 'sospesa'
(rifiutata dallo staff) o 'scaduta': un indice PARZIALE, limitato agli stati
'in_attesa_pagamento' e 'attiva', applica esattamente la stessa regola di
avvia_tesseramento() anche a livello DB.

Revision ID: 20260919_120000
Revises: 20260711_140000
Create Date: 2026-09-19 12:00:00
"""
from alembic import op

revision = "20260919_120000"
down_revision = "20260711_140000"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_tessere_socio_sport_anno_attiva"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "tessere",
        ["socio_id", "sport", "anno_sportivo"],
        unique=True,
        postgresql_where="stato IN ('in_attesa_pagamento', 'attiva')",
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="tessere")
