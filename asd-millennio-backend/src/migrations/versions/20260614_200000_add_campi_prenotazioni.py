"""Add slot_template_campo and prenotazioni_campo tables

Revision ID: 20260614_200000
Revises: 20260601_150000
Create Date: 2026-06-14 20:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260614_200000"
down_revision = "20260601_150000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slot_template_campo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("giorno_settimana", sa.SmallInteger, nullable=False),
        sa.Column("ora_inizio", sa.Time, nullable=False),
        sa.Column("ora_fine", sa.Time, nullable=False),
        sa.Column("num_campi", sa.SmallInteger, nullable=False, server_default="4"),
        sa.Column("costo_ora", sa.Numeric(8, 2), nullable=False),
        sa.Column("sport", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("attivo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("valido_dal", sa.Date, nullable=False),
        sa.Column("valido_fino_al", sa.Date, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create ENUM via raw SQL to avoid SQLAlchemy's double-create issue in Alembic
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE stato_prenotazione AS ENUM ('bloccata', 'confermata', 'cancellata', 'scaduta');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prenotazioni_campo (
            id UUID PRIMARY KEY,
            socio_id UUID NOT NULL REFERENCES soci(id),
            template_id UUID NOT NULL REFERENCES slot_template_campo(id),
            data DATE NOT NULL,
            ora_inizio TIME NOT NULL,
            ora_fine TIME NOT NULL,
            campo SMALLINT NOT NULL,
            importo_eur NUMERIC(8,2) NOT NULL,
            stato stato_prenotazione NOT NULL DEFAULT 'bloccata',
            stripe_session_id VARCHAR UNIQUE,
            bloccata_fino_a TIMESTAMPTZ,
            cancellabile_fino_a TIMESTAMPTZ,
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.create_index("ix_prenotazioni_campo_socio_id", "prenotazioni_campo", ["socio_id"])
    op.create_index("ix_prenotazioni_campo_template_id", "prenotazioni_campo", ["template_id"])
    op.create_index("ix_prenotazioni_campo_data", "prenotazioni_campo", ["data"])

    # Seed slot predefinito: Sabato 16:30–19:30, 4 campi badminton/pickleball
    op.execute("""
        INSERT INTO slot_template_campo
            (id, giorno_settimana, ora_inizio, ora_fine, num_campi, costo_ora, sport,
             attivo, valido_dal, valido_fino_al, note)
        VALUES
            (gen_random_uuid(), 5, '16:30', '19:30', 4, 30.00,
             ARRAY['badminton','pickleball'], true,
             CURRENT_DATE, '2027-07-31', 'Slot predefinito sabato pomeriggio')
    """)


def downgrade() -> None:
    op.drop_index("ix_prenotazioni_campo_data", table_name="prenotazioni_campo")
    op.drop_index("ix_prenotazioni_campo_template_id", table_name="prenotazioni_campo")
    op.drop_index("ix_prenotazioni_campo_socio_id", table_name="prenotazioni_campo")
    op.drop_table("prenotazioni_campo")
    op.execute("DROP TYPE IF EXISTS stato_prenotazione")
    op.drop_table("slot_template_campo")
