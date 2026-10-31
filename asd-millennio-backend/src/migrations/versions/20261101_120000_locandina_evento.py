"""Eventi campo: locandina pubblica

Una locandina (immagine) per evento, mostrata in home e nella pagina prenotazioni.
L'immagine sta in una tabella a parte, così le liste di eventi non la caricano.

Revision ID: 20261101_120000
Revises: 20261031_120000
Create Date: 2026-11-01 12:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261101_120000"
down_revision = "20261031_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eventi_campo", sa.Column("locandina_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "locandine_evento",
        sa.Column(
            "evento_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("eventi_campo.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("contenuto", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("larghezza", sa.SmallInteger(), nullable=False),
        sa.Column("altezza", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("locandine_evento")
    op.drop_column("eventi_campo", "locandina_at")
