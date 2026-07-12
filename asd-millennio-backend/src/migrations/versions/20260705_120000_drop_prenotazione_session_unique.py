"""Rimuove il vincolo UNIQUE su prenotazioni_campo.stripe_session_id

Il flusso "carrello → pagamento unico" fa condividere la stessa sessione Stripe
a più prenotazioni (una per ogni ora del carrello), quindi stripe_session_id non
può più essere UNIQUE. Sostituito con un indice normale per le lookup del webhook
(conferma_pagamento cerca tutte le prenotazioni con quella session).

Revision ID: 20260705_120000
Revises: 20260620_120000
Create Date: 2026-07-05 12:00:00
"""
from alembic import op

revision = "20260705_120000"
down_revision = "20260620_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE prenotazioni_campo "
        "DROP CONSTRAINT IF EXISTS prenotazioni_campo_stripe_session_id_key"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prenotazioni_campo_stripe_session "
        "ON prenotazioni_campo (stripe_session_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_prenotazioni_campo_stripe_session")
    # NB: fallisce se esistono più prenotazioni che condividono la stessa sessione
    # (dati creati col modello carrello) — atteso, il downgrade è un'operazione limite.
    op.execute(
        "ALTER TABLE prenotazioni_campo "
        "ADD CONSTRAINT prenotazioni_campo_stripe_session_id_key UNIQUE (stripe_session_id)"
    )
