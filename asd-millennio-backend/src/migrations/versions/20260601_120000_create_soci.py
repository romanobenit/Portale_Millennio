"""create soci e tessere

Revision ID: 20260601_120000
Revises:
Create Date: 2026-06-01 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260601_120000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "soci",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("cognome", sa.String(), nullable=False),
        sa.Column("data_nascita", sa.Date(), nullable=False),
        sa.Column("codice_fiscale", sa.String(16), unique=True, nullable=False),
        sa.Column("indirizzo", sa.Text()),
        sa.Column("email", sa.String(), unique=True, nullable=False),
        sa.Column("telefono", sa.String()),
        sa.Column("foto_url", sa.Text()),
        sa.Column("is_minor", sa.Boolean(), default=False, nullable=False),
        sa.Column("tutore_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id")),
        sa.Column("sport", postgresql.ARRAY(sa.String()), default=list),
        sa.Column("keycloak_user_id", sa.String(), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_soci_email", "soci", ["email"])
    op.create_index("ix_soci_codice_fiscale", "soci", ["codice_fiscale"])

    op.create_table(
        "tessere",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False, index=True),
        sa.Column("numero_tessera", sa.String(), unique=True, nullable=False),
        sa.Column("sport", sa.String(), nullable=False),
        sa.Column("stato", sa.Enum("bozza","in_attesa_pagamento","attiva","scaduta","sospesa", name="stato_tessera"), nullable=False, default="bozza"),
        sa.Column("data_emissione", sa.Date()),
        sa.Column("data_scadenza", sa.Date()),
        sa.Column("anno_sportivo", sa.String()),
        sa.Column("pdf_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "consensi",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False, index=True),
        sa.Column("tipo", sa.Enum("privacy","trattamento_dati","foto_video","marketing", name="tipo_consenso"), nullable=False),
        sa.Column("testo_versione", sa.String()),
        sa.Column("firmato_da", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id")),
        sa.Column("timestamp_firma", sa.DateTime(timezone=True)),
        sa.Column("revocato_at", sa.DateTime(timezone=True)),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN NEW.updated_at = now(); RETURN NEW; END;
        $$ LANGUAGE plpgsql;
    """)

    for table in ("soci", "tessere"):
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
        """)


def downgrade() -> None:
    for table in ("soci", "tessere"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at")
    op.drop_table("consensi")
    op.execute("DROP TYPE IF EXISTS tipo_consenso")
    op.drop_table("tessere")
    op.execute("DROP TYPE IF EXISTS stato_tessera")
    op.drop_table("soci")
