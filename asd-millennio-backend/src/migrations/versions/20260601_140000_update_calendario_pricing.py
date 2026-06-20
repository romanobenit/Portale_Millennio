"""Ristruttura slot_calendario (ore_vendute, rimuove ATI) e crea pricing_rules

Revision ID: 20260601_140000
Revises: 20260601_130000
Create Date: 2026-06-01 14:00:00
"""
from alembic import op

revision = "20260601_140000"
down_revision = "20260601_130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── slot_calendario: drop e ricrea con nuovo schema ──────────────────────
    op.execute("DROP TABLE IF EXISTS acquisto_nft_slots")
    op.execute("DROP TABLE IF EXISTS slot_calendario")
    op.execute("DROP TYPE IF EXISTS stato_slot")
    op.execute("DROP TYPE IF EXISTS associazione_slot")

    op.execute("""
        CREATE TYPE stato_slot AS ENUM ('libero','parziale','esaurito','bloccato')
    """)

    # Tutto SQL grezzo: evita che SQLAlchemy emetta CREATE TYPE per enum già esistenti
    op.execute("""
        CREATE TABLE slot_calendario (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            data DATE NOT NULL,
            fascia fascia_oraria NOT NULL,
            ora_inizio TIME NOT NULL,
            ora_fine TIME NOT NULL,
            ore_totali SMALLINT NOT NULL,
            ore_vendute INTEGER[] NOT NULL DEFAULT '{}',
            ore_in_lock INTEGER[] NOT NULL DEFAULT '{}',
            stato stato_slot NOT NULL DEFAULT 'libero',
            nft_token_id INTEGER,
            bloccato_fino_a TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_slot_data_fascia UNIQUE (data, fascia)
        )
    """)
    op.execute("CREATE INDEX ix_slot_calendario_data ON slot_calendario (data)")

    op.execute("""
        CREATE TRIGGER trg_slot_calendario_updated_at
        BEFORE UPDATE ON slot_calendario
        FOR EACH ROW EXECUTE FUNCTION update_updated_at()
    """)

    # ─── acquisto_nft_slots: ricrea con ore_acquistate ────────────────────────
    op.execute("""
        CREATE TABLE acquisto_nft_slots (
            acquisto_nft_id UUID NOT NULL REFERENCES acquisti_nft(id),
            slot_calendario_id UUID NOT NULL REFERENCES slot_calendario(id),
            ore_acquistate INTEGER[] NOT NULL DEFAULT '{}',
            PRIMARY KEY (acquisto_nft_id, slot_calendario_id)
        )
    """)

    # ─── pricing_rules ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE tipo_pricing_rule AS ENUM (
            'tariffa_base', 'leva_data', 'leva_scarsita', 'sconto_promo'
        )
    """)
    op.execute("""
        CREATE TYPE fascia_oraria_opt AS ENUM ('notte','mattina','pomeriggio')
    """)

    op.execute("""
        CREATE TABLE pricing_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tipo tipo_pricing_rule NOT NULL,
            fascia fascia_oraria_opt,
            soglia_min NUMERIC(8,2),
            soglia_max NUMERIC(8,2),
            valore NUMERIC(10,4) NOT NULL,
            attivo BOOLEAN NOT NULL DEFAULT true,
            nome VARCHAR(200) NOT NULL,
            valido_fino_a VARCHAR(10),
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TRIGGER trg_pricing_rules_updated_at
        BEFORE UPDATE ON pricing_rules
        FOR EACH ROW EXECUTE FUNCTION update_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_pricing_rules_updated_at ON pricing_rules")
    op.execute("DROP TABLE IF EXISTS pricing_rules")
    op.execute("DROP TYPE IF EXISTS fascia_oraria_opt")
    op.execute("DROP TYPE IF EXISTS tipo_pricing_rule")

    op.execute("DROP TRIGGER IF EXISTS trg_slot_calendario_updated_at ON slot_calendario")
    op.execute("DROP TABLE IF EXISTS acquisto_nft_slots")
    op.execute("DROP TABLE IF EXISTS slot_calendario")
    op.execute("DROP TYPE IF EXISTS stato_slot")

    # Ricrea versione precedente (senza ATI — downgrade parziale accettabile in dev)
    op.execute("""
        CREATE TYPE stato_slot AS ENUM ('libero','nft_venduto','ati_occupato','bloccato')
    """)
    op.execute("""
        CREATE TYPE associazione_slot AS ENUM ('millennio','ati')
    """)
    op.execute("""
        CREATE TABLE slot_calendario (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            data DATE NOT NULL,
            fascia fascia_oraria NOT NULL,
            ora_inizio TIME NOT NULL,
            ora_fine TIME NOT NULL,
            stato stato_slot NOT NULL DEFAULT 'libero',
            nft_token_id INTEGER,
            bloccato_fino_a TIMESTAMPTZ,
            associazione associazione_slot NOT NULL DEFAULT 'millennio',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE acquisto_nft_slots (
            acquisto_nft_id UUID NOT NULL REFERENCES acquisti_nft(id),
            slot_calendario_id UUID NOT NULL REFERENCES slot_calendario(id),
            PRIMARY KEY (acquisto_nft_id, slot_calendario_id)
        )
    """)
