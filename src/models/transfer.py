"""
Modèle Transaction
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, ForeignKey, DateTime, Index, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, VARCHAR
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


from .enums import TransactionStatus


class Transfer(BaseModel):
    __tablename__ = "transfers"
    __table_args__ = (
        Index("idx_transfer_status", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now, nullable=False)
    reference = Column(VARCHAR(50), unique=True, index=True, nullable=False)

    # Informations géographiques
    sender_country = Column(VARCHAR(200), nullable=False)
    receiver_country = Column(VARCHAR(200), nullable=False)
    sender_partner = Column(VARCHAR(20), nullable=False)
    receiver_partner = Column(VARCHAR(200), nullable=False)

    # Informations sur l'expéditeur et le destinataire
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_full_name = Column(VARCHAR(100), nullable=False)
    receiver_phone = Column(VARCHAR(20), nullable=False)
    receiver_email = Column(VARCHAR(100), nullable=True)

    # Montants et taux
    sender_amount = Column(DECIMAL(precision=15, scale=0), nullable=False)
    sender_currency = Column(VARCHAR(10), nullable=False)
    receiver_amount = Column(DECIMAL(precision=15, scale=0), nullable=False)
    receiver_currency = Column(VARCHAR(10), nullable=False)
    exchange_rate = Column(DECIMAL(precision=10, scale=4), nullable=False)

    # Frais
    applied_fee = Column(DECIMAL(precision=10, scale=2), nullable=False, default=0)
    total_to_pay = Column(DECIMAL(precision=15, scale=0), nullable=False)

    # Statut et suivi
    status = Column(VARCHAR(20), nullable=False, default=TransactionStatus.AWAITING_PAYMENT.value)
    notes = Column(VARCHAR(255), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)

    # Métadonnées supplémentaires
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    sender = relationship("User", back_populates="transfers_sent")

    def __repr__(self):
        return f"Transaction(id={self.id}, reference={self.reference}, status={self.status})"