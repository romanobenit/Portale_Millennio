"""Credito interno: registro dei movimenti e pagamento eventi col credito

Il credito è un semplice registro per i servizi dell'associazione: accrediti e
ricariche in sede della dirigenza, ricariche online (Stripe, disattivabili),
pagamento degli ingressi agli eventi e rimborso degli annullamenti in credito.
Niente trasferimenti fra soci né prelievi. Le righe del registro sono immutabili.

Revision ID: 20261026_120000
Revises: 20261025_120000
Create Date: 2026-10-26 12:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261026_120000"
down_revision = "20261025_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tipo = postgresql.ENUM(
        "accredito", "storno", "ricarica_sede", "ricarica_online", "pagamento_evento", "rimborso_evento",
        name="tipo_movimento_credito", create_type=False,
    )
    tipo.create(bind, checkfirst=True)

    op.create_table(
        "movimenti_credito",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False),
        sa.Column("tipo", tipo, nullable=False),
        sa.Column("importo_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("saldo_dopo_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("causale", sa.Text(), nullable=True),
        sa.Column("prenotazione_evento_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("prenotazioni_evento.id"), nullable=True),
        sa.Column("stripe_session_id", sa.String(), nullable=True, unique=True),
        sa.Column("stripe_payment_intent_id", sa.String(), nullable=True),
        sa.Column("operatore_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("importo_eur <> 0", name="ck_movimenti_credito_importo"),
    )
    op.create_index("ix_movimenti_credito_socio_id", "movimenti_credito", ["socio_id"])
    op.create_index("ix_movimenti_credito_prenotazione_evento_id", "movimenti_credito", ["prenotazione_evento_id"])
    op.create_index("ix_movimenti_credito_stripe_payment_intent_id", "movimenti_credito", ["stripe_payment_intent_id"])
    # Un solo addebito e un solo rimborso per prenotazione (idempotenza)
    op.create_index(
        "uq_movimenti_credito_prenotazione_tipo", "movimenti_credito", ["prenotazione_evento_id", "tipo"],
        unique=True, postgresql_where=sa.text("prenotazione_evento_id IS NOT NULL"),
    )
    op.execute("""
        CREATE FUNCTION movimenti_credito_immutabili() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Il registro del credito non si modifica: registra un movimento di storno';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_movimenti_credito_immutabili
        BEFORE UPDATE OR DELETE ON movimenti_credito
        FOR EACH ROW EXECUTE FUNCTION movimenti_credito_immutabili()
    """)

    op.add_column(
        "prenotazioni_evento",
        sa.Column("pagato_con_credito", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("prenotazioni_evento", "pagato_con_credito")
    op.execute("DROP TRIGGER IF EXISTS trg_movimenti_credito_immutabili ON movimenti_credito")
    op.execute("DROP FUNCTION IF EXISTS movimenti_credito_immutabili()")
    op.drop_table("movimenti_credito")
    postgresql.ENUM(name="tipo_movimento_credito").drop(op.get_bind(), checkfirst=True)
