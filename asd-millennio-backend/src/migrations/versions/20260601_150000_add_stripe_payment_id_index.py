"""Aggiunge indice su acquisto_nft.stripe_payment_id per performance webhook

Il webhook payment_intent.payment_failed e charge.refunded fanno lookup su
stripe_payment_id. Senza indice ogni evento esegue full table scan.

Revision ID: 20260601_150000
Revises: 20260601_140000
Create Date: 2026-06-01 15:00:00
"""
from alembic import op

revision = "20260601_150000"
down_revision = "20260601_140000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_acquisto_nft_stripe_payment_id",
        "acquisti_nft",
        ["stripe_payment_id"],
        unique=False,
        postgresql_where="stripe_payment_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("ix_acquisto_nft_stripe_payment_id", table_name="acquisti_nft")
