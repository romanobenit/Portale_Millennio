"""Tracker iscritti: contatti, storico degli stati, costi istruttore

Registro dei contatti interessati agli sport (fonte, sport, stato) per capire quali
sport e quali fonti portano iscritti paganti. Lo storico degli stati permette di
contare chi ha raggiunto ogni fase; i costi istruttore servono al margine per sport.

Revision ID: 20261115_120000
Revises: 20261101_120000
Create Date: 2026-11-15 12:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261115_120000"
down_revision = "20261101_120000"
branch_labels = None
depends_on = None

ENUMS = {
    "sport_tracker": (
        "kung_fu", "pallavolo", "badminton", "pickleball", "tornei_pickleball", "basket_serale", "calcio_a_5",
    ),
    "fonte_contatto": ("meta_ads", "organico", "torneo", "passaggio_struttura", "passaparola", "altro"),
    "canale_contatto": ("whatsapp", "email", "instagram"),
    "stato_contatto": ("lead", "prova_prenotata", "prova_svolta", "iscritto", "pagato", "perso"),
    "tipo_abbonamento_tracker": ("mensile", "annuale"),
}


def _enum(nome: str) -> postgresql.ENUM:
    return postgresql.ENUM(*ENUMS[nome], name=nome, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for nome in ENUMS:
        _enum(nome).create(bind, checkfirst=True)

    op.create_table(
        "membri_tracker",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("keycloak_user_id", sa.String(), nullable=False, unique=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("ruolo", sa.String(), nullable=False),
        sa.Column("ultimo_accesso", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "contatti_tracker",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_contatto", sa.Date(), nullable=False),
        sa.Column("sport", _enum("sport_tracker"), nullable=False),
        sa.Column("fonte", _enum("fonte_contatto"), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("canale", _enum("canale_contatto"), nullable=True),
        sa.Column("recapito", sa.String(120), nullable=True),
        sa.Column("stato", _enum("stato_contatto"), nullable=False),
        sa.Column("data_prova", sa.Date(), nullable=True),
        sa.Column("tipo_abbonamento", _enum("tipo_abbonamento_tracker"), nullable=True),
        sa.Column("importo_eur", sa.Numeric(10, 2), nullable=True),
        sa.Column("responsabile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("membri_tracker.id"), nullable=True),
        sa.Column("prossimo_followup", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creato_da_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("membri_tracker.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("importo_eur IS NULL OR importo_eur >= 0", name="ck_contatti_tracker_importo"),
    )
    for col in ("data_contatto", "sport", "fonte", "stato", "responsabile_id", "prossimo_followup"):
        op.create_index(f"ix_contatti_tracker_{col}", "contatti_tracker", [col])
    op.execute("""
        CREATE TRIGGER trg_contatti_tracker_updated_at
        BEFORE UPDATE ON contatti_tracker
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)

    op.create_table(
        "contatti_tracker_stati",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contatto_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contatti_tracker.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stato", _enum("stato_contatto"), nullable=False),
        sa.Column("cambiato_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cambiato_da_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("membri_tracker.id"), nullable=True),
    )
    op.create_index("ix_contatti_tracker_stati_contatto_id", "contatti_tracker_stati", ["contatto_id"])

    op.create_table(
        "costi_istruttore",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sport", _enum("sport_tracker"), nullable=False),
        sa.Column("valido_dal", sa.Date(), nullable=False),
        sa.Column("costo_mensile_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("sport", "valido_dal", name="uq_costo_istruttore_sport_mese"),
        sa.CheckConstraint("costo_mensile_eur >= 0", name="ck_costi_istruttore_costo"),
        sa.CheckConstraint("EXTRACT(DAY FROM valido_dal) = 1", name="ck_costi_istruttore_primo_del_mese"),
    )


def downgrade() -> None:
    op.drop_table("costi_istruttore")
    op.drop_table("contatti_tracker_stati")
    op.execute("DROP TRIGGER IF EXISTS trg_contatti_tracker_updated_at ON contatti_tracker")
    op.drop_table("contatti_tracker")
    op.drop_table("membri_tracker")
    bind = op.get_bind()
    for nome in reversed(list(ENUMS)):
        _enum(nome).drop(bind, checkfirst=True)
