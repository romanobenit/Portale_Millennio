"""token_id unico per contratto invece che globale

Dopo un redeploy del contratto, i token_id ripartono da 0 e collidono con gli
acquisti storici se token_id ha un vincolo UNIQUE globale. Si sostituisce con
un vincolo composito (contract_address, token_id).

Revision ID: 20260620_120000
Revises: 20260614_200000
Create Date: 2026-06-20 12:00:00
"""
from alembic import op

revision = "20260620_120000"
down_revision = "20260614_200000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("acquisti_nft_token_id_key", "acquisti_nft", type_="unique")
    op.create_unique_constraint(
        "uq_acquisti_nft_contract_token",
        "acquisti_nft",
        ["contract_address", "token_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_acquisti_nft_contract_token", "acquisti_nft", type_="unique")
    op.create_unique_constraint(
        "acquisti_nft_token_id_key", "acquisti_nft", ["token_id"]
    )
