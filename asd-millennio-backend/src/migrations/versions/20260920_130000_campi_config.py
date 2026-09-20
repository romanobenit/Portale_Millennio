"""Configurazione campi: orizzonte_giorni della disponibilità prenotabile

Il "prossimi 60 giorni" della pagina prenotazioni era fisso nel frontend.
Aggiunge una tabella singleton (`campi_config`) configurabile dalla dirigenza
(§Gestione Campi) e la popola con una riga di default che preserva il
comportamento attuale (60 giorni).

Revision ID: 20260920_130000
Revises: 20260919_120000
Create Date: 2026-09-20 13:00:00
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260920_130000"
down_revision = "20260919_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campi_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("orizzonte_giorni", sa.SmallInteger(), nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    campi_config = sa.table(
        "campi_config",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("orizzonte_giorni", sa.SmallInteger()),
    )
    op.bulk_insert(campi_config, [{"id": uuid.uuid4(), "orizzonte_giorni": 60}])


def downgrade() -> None:
    op.drop_table("campi_config")
