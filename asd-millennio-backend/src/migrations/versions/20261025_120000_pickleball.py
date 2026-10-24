"""Pickleball: partite, classifica Elo interna (singolo/doppio), profilo atleta

Risultati inseriti dai giocatori (conferma dell'avversario) o dalla dirigenza
(tornei). Il punteggio è un Elo interno del club, ricalcolato dalle partite
confermate; DUPR è solo dichiarato dal socio (proprietario, non calcolabile).

Revision ID: 20261025_120000
Revises: 20261024_120000
Create Date: 2026-10-25 12:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261025_120000"
down_revision = "20261024_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    formato = postgresql.ENUM("singolo", "doppio", name="formato_partita", create_type=False)
    stato = postgresql.ENUM("in_attesa_conferma", "confermata", "contestata", "annullata",
                            name="stato_partita", create_type=False)
    formato.create(bind, checkfirst=True)
    stato.create(bind, checkfirst=True)

    op.create_table(
        "partite_pickleball",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("formato", formato, nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("punteggi", postgresql.JSONB(), nullable=False),
        sa.Column("vincitore", sa.String(1), nullable=False),
        sa.Column("stato", stato, nullable=False, server_default="in_attesa_conferma"),
        sa.Column("torneo", sa.String(), nullable=True),
        sa.Column("evento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eventi_campo.id"), nullable=True),
        sa.Column("inserita_da", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=True),
        sa.Column("inserita_da_dirigenza", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confermata_da", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=True),
        sa.Column("confermata_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("vincitore IN ('a', 'b')", name="ck_partite_pickleball_vincitore"),
    )
    op.create_index("ix_partite_pickleball_data", "partite_pickleball", ["data"])
    op.create_index("ix_partite_pickleball_stato", "partite_pickleball", ["stato"])

    op.create_table(
        "partite_pickleball_giocatori",
        sa.Column("partita_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("partite_pickleball.id", ondelete="CASCADE"), nullable=False),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False),
        sa.Column("squadra", sa.String(1), nullable=False),
        sa.Column("rating_prima", sa.Numeric(7, 2), nullable=True),
        sa.Column("rating_dopo", sa.Numeric(7, 2), nullable=True),
        sa.PrimaryKeyConstraint("partita_id", "socio_id"),
        sa.CheckConstraint("squadra IN ('a', 'b')", name="ck_partite_giocatori_squadra"),
    )
    op.create_index("ix_partite_pickleball_giocatori_socio_id", "partite_pickleball_giocatori", ["socio_id"])

    op.create_table(
        "rating_pickleball",
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=False),
        sa.Column("formato", formato, nullable=False),
        sa.Column("rating", sa.Numeric(7, 2), nullable=False),
        sa.Column("rating_max", sa.Numeric(7, 2), nullable=False),
        sa.Column("partite", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vittorie", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ultima_partita", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("socio_id", "formato"),
    )

    op.create_table(
        "profili_atleta",
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), primary_key=True),
        sa.Column("visibile_in_classifica", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("obiettivo_singolo", sa.SmallInteger(), nullable=True),
        sa.Column("obiettivo_doppio", sa.SmallInteger(), nullable=True),
        sa.Column("obiettivo_partite_mese", sa.SmallInteger(), nullable=True),
        sa.Column("dupr_id", sa.String(), nullable=True),
        sa.Column("dupr_singolo", sa.Numeric(4, 3), nullable=True),
        sa.Column("dupr_doppio", sa.Numeric(4, 3), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("profili_atleta")
    op.drop_table("rating_pickleball")
    op.drop_table("partite_pickleball_giocatori")
    op.drop_table("partite_pickleball")
    bind = op.get_bind()
    for name in ("stato_partita", "formato_partita"):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
