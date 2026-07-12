"""Tesseramento self-service: verifica tessere, documenti, quote, pagamento tessera

Fase 1 (dati + storage) del flusso di auto-tesseramento:
- campi di verifica su `tessere` (attiva provvisoria → conferma staff / silenzio-assenso);
- `documenti_socio` (metadati dei documenti sensibili cifrati su volume privato);
- `quote_tessera` (quote associative gestite dalla dirigenza, per categoria/minore/anno);
- `pagamento_tessera` (pagamento Stripe della quota; su rifiuto → erogazione liberale).

Revision ID: 20260711_140000
Revises: 20260711_120000
Create Date: 2026-07-11 14:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260711_140000"
down_revision = "20260711_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    verifica_enum = postgresql.ENUM(
        "in_verifica", "confermata", "rifiutata",
        name="verifica_tessera",
    )
    verifica_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("tessere", sa.Column("verifica_stato", verifica_enum, nullable=True))
    op.add_column("tessere", sa.Column("verifica_scadenza", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tessere", sa.Column("verificata_da", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tessere", sa.Column("verificata_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_tessere_verificata_da_soci", "tessere", "soci", ["verificata_da"], ["id"]
    )

    op.create_table(
        "documenti_socio",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False),
        sa.Column("tipo", postgresql.ENUM("identita", "tutela", name="tipo_documento"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("caricato_da", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documenti_socio_socio_id", "documenti_socio", ["socio_id"])

    op.create_table(
        "quote_tessera",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("is_minore", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("importo_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("anno_sportivo", sa.String(), nullable=False),
        sa.Column("attivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("categoria", "is_minore", "anno_sportivo", name="uq_quota_cat_minore_anno"),
    )

    op.create_table(
        "pagamento_tessera",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tessera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tessere.id"), nullable=False),
        sa.Column("pagante_socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False),
        sa.Column("stripe_session_id", sa.String(), nullable=False, unique=True),
        sa.Column("stripe_payment_id", sa.String(), nullable=True),
        sa.Column("importo_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "stato",
            postgresql.ENUM(
                "in_attesa_pagamento", "pagato", "rimborsato", "erogazione_liberale",
                name="stato_pagamento_tessera",
            ),
            nullable=False,
            server_default="in_attesa_pagamento",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pagamento_tessera_tessera_id", "pagamento_tessera", ["tessera_id"])


def downgrade() -> None:
    op.drop_table("pagamento_tessera")
    op.drop_table("quote_tessera")
    op.drop_index("ix_documenti_socio_socio_id", table_name="documenti_socio")
    op.drop_table("documenti_socio")
    op.drop_constraint("fk_tessere_verificata_da_soci", "tessere", type_="foreignkey")
    op.drop_column("tessere", "verificata_at")
    op.drop_column("tessere", "verificata_da")
    op.drop_column("tessere", "verifica_scadenza")
    op.drop_column("tessere", "verifica_stato")
    op.execute("DROP TYPE IF EXISTS verifica_tessera")
    op.execute("DROP TYPE IF EXISTS tipo_documento")
    op.execute("DROP TYPE IF EXISTS stato_pagamento_tessera")
