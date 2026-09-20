"""Certificato medico sulla tessera (informativo, self-service)

Aggiunge il tracciamento del certificato di idoneità sportiva: tipo
(non_agonistico/agonistico) e scadenza sulla tessera, più un nuovo tipo
'certificato_medico' nel meccanismo di upload documenti cifrati già
esistente (stesso storage di identità/tutela). Non blocca l'attivazione
della tessera — è solo tracciato/visibile per la dirigenza.

Revision ID: 20260920_140000
Revises: 20260920_130000
Create Date: 2026-09-20 14:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260920_140000"
down_revision = "20260920_130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tipo_certificato_medico = postgresql.ENUM(
        "non_agonistico", "agonistico",
        name="tipo_certificato_medico",
    )
    tipo_certificato_medico.create(op.get_bind(), checkfirst=True)

    op.add_column("tessere", sa.Column("certificato_medico_tipo", tipo_certificato_medico, nullable=True))
    op.add_column("tessere", sa.Column("certificato_medico_scadenza", sa.Date(), nullable=True))

    # Nuovo valore nell'enum esistente tipo_documento — additivo, non tocca i
    # valori già presenti (identita, tutela) né le righe esistenti.
    op.execute("ALTER TYPE tipo_documento ADD VALUE IF NOT EXISTS 'certificato_medico'")


def downgrade() -> None:
    # Postgres non supporta la rimozione di un valore da un ENUM — il downgrade
    # rimuove solo le colonne aggiunte su tessere, il valore 'certificato_medico'
    # resta nell'enum tipo_documento (innocuo se non più referenziato).
    op.drop_column("tessere", "certificato_medico_scadenza")
    op.drop_column("tessere", "certificato_medico_tipo")
    op.execute("DROP TYPE IF EXISTS tipo_certificato_medico")
