"""Aggiunge acquisti_nft.mint_tx_hash

Salva l'hash della transazione di conio dell'NFT su Polygon. Serve per il
certificato di sostegno (PDF) e per il link diretto alla tx su Polygonscan.
Prima non veniva persistito: il worker mintava ma buttava via il tx hash.

Revision ID: 20260711_120000
Revises: 20260705_120000
Create Date: 2026-07-11 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20260711_120000"
down_revision = "20260705_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("acquisti_nft", sa.Column("mint_tx_hash", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("acquisti_nft", "mint_tx_hash")
