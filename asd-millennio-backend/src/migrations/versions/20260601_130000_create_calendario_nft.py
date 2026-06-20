"""create calendario slot e acquisti NFT

Revision ID: 20260601_130000
Revises: 20260601_120000
Create Date: 2026-06-01 13:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260601_130000"
down_revision = "20260601_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slot_calendario",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data", sa.Date(), nullable=False, index=True),
        sa.Column("fascia", sa.Enum("notte","mattina","pomeriggio", name="fascia_oraria"), nullable=False),
        sa.Column("ora_inizio", sa.Time(), nullable=False),
        sa.Column("ora_fine", sa.Time(), nullable=False),
        sa.Column("stato", sa.Enum("libero","nft_venduto","ati_occupato","bloccato", name="stato_slot"), nullable=False, default="libero"),
        sa.Column("nft_token_id", sa.Integer()),
        sa.Column("bloccato_fino_a", sa.DateTime(timezone=True)),
        sa.Column("associazione", sa.Enum("millennio","ati", name="associazione_slot"), nullable=False, default="millennio"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "acquisti_nft",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False, index=True),
        sa.Column("stripe_session_id", sa.String(), unique=True, nullable=False),
        sa.Column("stripe_payment_id", sa.String()),
        sa.Column("token_id", sa.Integer(), unique=True),
        sa.Column("contract_address", sa.String()),
        sa.Column("ipfs_uri", sa.String()),
        sa.Column("ical_sha256", sa.String()),
        sa.Column("importo_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("stato", sa.Enum("in_attesa_pagamento","pagato","mintato","fallito","rimborsato", name="stato_acquisto"), nullable=False, default="in_attesa_pagamento"),
        sa.Column("acquisto_per_minore", sa.Boolean(), default=False),
        sa.Column("minore_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id")),
        sa.Column("wallet_address", sa.String()),
        sa.Column("metadati_json", sa.Text()),
        sa.Column("ical_content", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "acquisto_nft_slots",
        sa.Column("acquisto_nft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("acquisti_nft.id"), primary_key=True),
        sa.Column("slot_calendario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("slot_calendario.id"), primary_key=True),
    )

    op.create_table(
        "accesso_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_id", sa.Integer(), nullable=False, index=True),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id")),
        sa.Column("slot_key", sa.String(), nullable=False),
        sa.Column("verificato_da", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id")),
        sa.Column("esito", sa.Enum("valido","non_valido","slot_errato","tessera_scaduta", name="esito_accesso"), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("note", sa.Text()),
    )

    op.create_table(
        "wallet_custodiali",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), unique=True, nullable=False, index=True),
        sa.Column("wallet_address", sa.String(), unique=True, nullable=False),
        sa.Column("encrypted_private_key", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "webhook_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("webhook_id", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.Text()),
        sa.Column("processed", sa.Boolean(), default=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.execute("""
        CREATE TRIGGER trg_acquisti_nft_updated_at
        BEFORE UPDATE ON acquisti_nft
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_acquisti_nft_updated_at ON acquisti_nft")
    op.drop_table("webhook_log")
    op.drop_table("wallet_custodiali")
    op.drop_table("accesso_log")
    op.execute("DROP TYPE IF EXISTS esito_accesso")
    op.drop_table("acquisto_nft_slots")
    op.drop_table("acquisti_nft")
    op.execute("DROP TYPE IF EXISTS stato_acquisto")
    op.drop_table("slot_calendario")
    op.execute("DROP TYPE IF EXISTS associazione_slot")
    op.execute("DROP TYPE IF EXISTS stato_slot")
    op.execute("DROP TYPE IF EXISTS fascia_oraria")
