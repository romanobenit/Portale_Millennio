"""Iscrizione community con tessera di un'altra ASD

Si entra nella community anche senza tesserarsi alla Millennio, purché si
abbia la tessera di un'altra ASD (federazione o ente di promozione sportiva).
L'iscrizione è una tessera di categoria 'community' (prefisso COM, senza
scadenza); i dati della tessera esterna vivono in `tessere_esterne` con la
loro scadenza, che decide fino a quando si possono usare i campi.

Revision ID: 20261024_120000
Revises: 20261023_120000
Create Date: 2026-10-24 12:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261024_120000"
down_revision = "20261023_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE tipo_documento ADD VALUE IF NOT EXISTS 'tessera_esterna'")

    verifica = postgresql.ENUM("in_verifica", "confermata", "rifiutata", name="verifica_tessera", create_type=False)
    op.create_table(
        "tessere_esterne",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False),
        sa.Column("ente", sa.String(), nullable=False),
        sa.Column("asd_nome", sa.String(), nullable=False),
        sa.Column("asd_codice", sa.String(), nullable=True),
        sa.Column("numero_tessera", sa.String(), nullable=False),
        sa.Column("disciplina", sa.String(), nullable=False),
        sa.Column("data_scadenza", sa.Date(), nullable=False),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documenti_socio.id"), nullable=True),
        sa.Column("verifica_stato", verifica, nullable=False, server_default="in_verifica"),
        sa.Column("verifica_scadenza", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verificata_da", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=True),
        sa.Column("verificata_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("caricata_da", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tessere_esterne_socio_id", "tessere_esterne", ["socio_id"])
    op.create_index("ix_tessere_esterne_data_scadenza", "tessere_esterne", ["data_scadenza"])


def downgrade() -> None:
    op.drop_table("tessere_esterne")
    # il valore 'tessera_esterna' di tipo_documento resta: PostgreSQL non rimuove valori di enum
