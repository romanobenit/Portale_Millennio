"""Pickleball: tornei, ospiti, piazzamenti e circuito

- Tornei (sociali, open, federali): le loro partite pesano di più nell'Elo e i
  piazzamenti danno i punti del circuito stagionale.
- Ospiti: giocatori non soci incontrati nei tornei, con dati minimi; servono al
  calcolo dell'Elo dei soci e non compaiono in classifica. Per questo un giocatore
  di una partita è ora un socio OPPURE un ospite.
- Impostazioni modificabili dalla dirigenza (pesi, punti, limiti).

Revision ID: 20261031_120000
Revises: 20261026_120000
Create Date: 2026-10-31 12:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261031_120000"
down_revision = "20261026_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    livello = postgresql.ENUM("sociale", "open", "federale", name="livello_torneo", create_type=False)
    piazzamento = postgresql.ENUM(
        "vincitore", "finalista", "semifinalista", "fase_finale", "partecipazione", "nessuno",
        name="piazzamento_torneo", create_type=False,
    )
    formato = postgresql.ENUM("singolo", "doppio", name="formato_partita", create_type=False)
    livello.create(bind, checkfirst=True)
    piazzamento.create(bind, checkfirst=True)

    op.create_table(
        "tornei_pickleball",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("luogo", sa.String(), nullable=True),
        sa.Column("livello", livello, nullable=False, server_default="sociale"),
        sa.Column("anno_sportivo", sa.String(9), nullable=False),
        sa.Column("concluso", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("url_esterno", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tornei_pickleball_data", "tornei_pickleball", ["data"])
    op.create_index("ix_tornei_pickleball_anno_sportivo", "tornei_pickleball", ["anno_sportivo"])

    op.create_table(
        "giocatori_ospiti",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("cognome", sa.String(), nullable=False),
        sa.Column("club", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("sesso", sa.String(1), nullable=True),
        sa.Column("anno_nascita", sa.SmallInteger(), nullable=True),
        sa.Column("invitato_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sesso IS NULL OR sesso IN ('M', 'F')", name="ck_giocatori_ospiti_sesso"),
    )

    op.add_column("partite_pickleball", sa.Column(
        "torneo_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("tornei_pickleball.id", ondelete="CASCADE"), nullable=True,
    ))
    op.add_column("partite_pickleball", sa.Column("categoria", sa.String(20), nullable=True))
    op.add_column("partite_pickleball", sa.Column("fase", sa.String(20), nullable=True))
    op.add_column("partite_pickleball", sa.Column("walkover", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("partite_pickleball", sa.Column("fuori_classifica", sa.String(30), nullable=True))
    op.create_index("ix_partite_pickleball_torneo_id", "partite_pickleball", ["torneo_id"])

    # Un giocatore di una partita è un socio oppure un ospite: chiave surrogata
    op.add_column("partite_pickleball_giocatori", sa.Column(
        "id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()"),
    ))
    op.drop_constraint("partite_pickleball_giocatori_pkey", "partite_pickleball_giocatori", type_="primary")
    op.create_primary_key("partite_pickleball_giocatori_pkey", "partite_pickleball_giocatori", ["id"])
    op.alter_column("partite_pickleball_giocatori", "socio_id", nullable=True)
    op.add_column("partite_pickleball_giocatori", sa.Column(
        "ospite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("giocatori_ospiti.id"), nullable=True,
    ))
    op.create_check_constraint(
        "ck_partite_giocatori_socio_o_ospite", "partite_pickleball_giocatori",
        "(socio_id IS NULL) <> (ospite_id IS NULL)",
    )
    op.create_index("ix_partite_pickleball_giocatori_ospite_id", "partite_pickleball_giocatori", ["ospite_id"])
    op.create_index(
        "uq_partite_giocatori_socio", "partite_pickleball_giocatori", ["partita_id", "socio_id"],
        unique=True, postgresql_where=sa.text("socio_id IS NOT NULL"),
    )
    op.create_index(
        "uq_partite_giocatori_ospite", "partite_pickleball_giocatori", ["partita_id", "ospite_id"],
        unique=True, postgresql_where=sa.text("ospite_id IS NOT NULL"),
    )

    op.create_table(
        "rating_ospiti_pickleball",
        sa.Column("ospite_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("giocatori_ospiti.id", ondelete="CASCADE"), nullable=False),
        sa.Column("formato", formato, nullable=False),
        sa.Column("rating", sa.Numeric(7, 2), nullable=False),
        sa.Column("partite", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vittorie", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("ospite_id", "formato"),
    )

    op.create_table(
        "piazzamenti_torneo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("torneo_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tornei_pickleball.id", ondelete="CASCADE"), nullable=False),
        sa.Column("categoria", sa.String(20), nullable=False),
        sa.Column("socio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soci.id"), nullable=True),
        sa.Column("ospite_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("giocatori_ospiti.id", ondelete="CASCADE"), nullable=True),
        sa.Column("piazzamento", piazzamento, nullable=False),
        sa.Column("manuale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("(socio_id IS NULL) <> (ospite_id IS NULL)", name="ck_piazzamenti_socio_o_ospite"),
        sa.UniqueConstraint("torneo_id", "categoria", "socio_id", name="uq_piazzamento_socio"),
        sa.UniqueConstraint("torneo_id", "categoria", "ospite_id", name="uq_piazzamento_ospite"),
    )
    op.create_index("ix_piazzamenti_torneo_torneo_id", "piazzamenti_torneo", ["torneo_id"])
    op.create_index("ix_piazzamenti_torneo_socio_id", "piazzamenti_torneo", ["socio_id"])

    op.create_table(
        "config_pickleball",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("valori", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_config_pickleball_una_riga"),
    )


def downgrade() -> None:
    op.drop_table("config_pickleball")
    op.drop_table("piazzamenti_torneo")
    op.drop_table("rating_ospiti_pickleball")
    op.execute("DELETE FROM partite_pickleball_giocatori WHERE ospite_id IS NOT NULL")
    op.drop_index("uq_partite_giocatori_ospite", "partite_pickleball_giocatori")
    op.drop_index("uq_partite_giocatori_socio", "partite_pickleball_giocatori")
    op.drop_index("ix_partite_pickleball_giocatori_ospite_id", "partite_pickleball_giocatori")
    op.drop_constraint("ck_partite_giocatori_socio_o_ospite", "partite_pickleball_giocatori", type_="check")
    op.drop_column("partite_pickleball_giocatori", "ospite_id")
    op.alter_column("partite_pickleball_giocatori", "socio_id", nullable=False)
    op.drop_constraint("partite_pickleball_giocatori_pkey", "partite_pickleball_giocatori", type_="primary")
    op.create_primary_key("partite_pickleball_giocatori_pkey", "partite_pickleball_giocatori", ["partita_id", "socio_id"])
    op.drop_column("partite_pickleball_giocatori", "id")
    op.drop_index("ix_partite_pickleball_torneo_id", "partite_pickleball")
    for col in ("fuori_classifica", "walkover", "fase", "categoria", "torneo_id"):
        op.drop_column("partite_pickleball", col)
    op.drop_table("giocatori_ospiti")
    op.drop_table("tornei_pickleball")
    bind = op.get_bind()
    for name in ("piazzamento_torneo", "livello_torneo"):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
