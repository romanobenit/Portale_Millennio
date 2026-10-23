"""Eventi campo: prenotazione per evento al posto della prenotazione a ore

La dirigenza individua eventi (finestre di 1h30–2h) in cui il Palasirio è
utilizzabile; chi partecipa paga l'ingresso per tutta la durata, online
(Stripe) oppure in sede (solo tesserati). Posti limitati con lista d'attesa;
le assenze dei "pago in sede" segnate dalla dirigenza bloccano, dopo 2, la
modalità in sede finché la dirigenza non le azzera (soci.assenze_azzerate_at).

Le tabelle del vecchio sistema a ore (slot_template_campo, prenotazioni_campo)
restano intatte per lo storico.

Revision ID: 20261023_120000
Revises: 20260920_140000
Create Date: 2026-10-23 12:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261023_120000"
down_revision = "20260920_140000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    stato_evento = postgresql.ENUM("programmato", "annullato", name="stato_evento", create_type=False)
    modalita = postgresql.ENUM("online", "in_sede", name="modalita_prenotazione_evento", create_type=False)
    stato_pren = postgresql.ENUM(
        "in_attesa_pagamento", "confermata", "annullata", "scaduta", "rimborsata",
        name="stato_prenotazione_evento", create_type=False,
    )
    presenza = postgresql.ENUM("presente", "assente", name="presenza_evento", create_type=False)
    for e in (stato_evento, modalita, stato_pren, presenza):
        e.create(bind, checkfirst=True)

    op.create_table(
        "eventi_campo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("titolo", sa.String(), nullable=True),
        sa.Column("sport", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("ora_inizio", sa.Time(), nullable=False),
        sa.Column("ora_fine", sa.Time(), nullable=False),
        sa.Column("prezzo_eur", sa.Numeric(8, 2), nullable=False),
        sa.Column("posti_max", sa.SmallInteger(), nullable=False),
        sa.Column("presenze_manuali", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("stato", stato_evento, nullable=False, server_default="programmato"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("ora_fine > ora_inizio", name="ck_eventi_campo_orario"),
        sa.CheckConstraint("posti_max > 0", name="ck_eventi_campo_posti"),
    )
    op.create_index("ix_eventi_campo_data", "eventi_campo", ["data"])

    op.create_table(
        "prenotazioni_evento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eventi_campo.id"), nullable=False),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False),
        sa.Column("modalita", modalita, nullable=False),
        sa.Column("stato", stato_pren, nullable=False),
        sa.Column("importo_eur", sa.Numeric(8, 2), nullable=False),
        sa.Column("pagato_in_sede", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("presenza", presenza, nullable=True),
        sa.Column("presenza_segnata_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inserita_da_staff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stripe_session_id", sa.String(), nullable=True, unique=True),
        sa.Column("stripe_payment_intent_id", sa.String(), nullable=True),
        sa.Column("bloccata_fino_a", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_prenotazioni_evento_evento_id", "prenotazioni_evento", ["evento_id"])
    op.create_index("ix_prenotazioni_evento_socio_id", "prenotazioni_evento", ["socio_id"])
    op.create_index(
        "ix_prenotazioni_evento_stripe_payment_intent_id", "prenotazioni_evento", ["stripe_payment_intent_id"]
    )
    # Una sola prenotazione attiva per persona e evento (anti doppio click / doppia prenotazione).
    op.create_index(
        "uq_prenotazioni_evento_socio_attiva",
        "prenotazioni_evento",
        ["evento_id", "socio_id"],
        unique=True,
        postgresql_where=sa.text("stato IN ('in_attesa_pagamento', 'confermata')"),
    )

    op.create_table(
        "lista_attesa_evento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eventi_campo.id"), nullable=False),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False),
        sa.Column("notificato_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("evento_id", "socio_id", name="uq_lista_attesa_evento_socio"),
    )
    op.create_index("ix_lista_attesa_evento_evento_id", "lista_attesa_evento", ["evento_id"])
    op.create_index("ix_lista_attesa_evento_socio_id", "lista_attesa_evento", ["socio_id"])

    op.add_column("soci", sa.Column("assenze_azzerate_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("soci", "assenze_azzerate_at")
    op.drop_table("lista_attesa_evento")
    op.drop_table("prenotazioni_evento")
    op.drop_table("eventi_campo")
    bind = op.get_bind()
    for name in ("presenza_evento", "stato_prenotazione_evento", "modalita_prenotazione_evento", "stato_evento"):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
