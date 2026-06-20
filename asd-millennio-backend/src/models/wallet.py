import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class WalletCustodiale(Base):
    __tablename__ = "wallet_custodiali"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    socio_id = Column(UUID(as_uuid=True), ForeignKey("soci.id"), unique=True, nullable=False, index=True)
    wallet_address = Column(String, unique=True, nullable=False)
    encrypted_private_key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    socio = relationship("Socio")
