import uuid

from sqlalchemy import Boolean, Column, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class QuotaTessera(Base):
    """
    Quota associativa per categoria di tessera, gestita dalla dashboard dirigenza.
    Variabile per categoria (sport / 'sostenitore') e per adulto/minore, per anno sportivo.
    """
    __tablename__ = "quote_tessera"
    __table_args__ = (
        UniqueConstraint("categoria", "is_minore", "anno_sportivo", name="uq_quota_cat_minore_anno"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    categoria = Column(String, nullable=False)  # 'volley','badminton','kung_fu','pickleball','sostenitore'
    is_minore = Column(Boolean, nullable=False, default=False)
    importo_eur = Column(Numeric(10, 2), nullable=False)
    anno_sportivo = Column(String, nullable=False)
    attivo = Column(Boolean, nullable=False, default=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
