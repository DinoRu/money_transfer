"""
Modèle PaymentAccount
"""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, VARCHAR
from sqlalchemy.orm import relationship

from src.models.base import BaseModel



class PaymentAccount(BaseModel):
    __tablename__ = "payment_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    payment_partner_id = Column(UUID(as_uuid=True), ForeignKey("payment_partners.id"), nullable=False)
    account_name = Column(VARCHAR(100), nullable=False)
    account_number = Column(VARCHAR(20), nullable=True)
    bank_name = Column(VARCHAR(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relations
    payment_partner = relationship("PaymentPartner", back_populates="payment_accounts")

    def __repr__(self):
        return f"PaymentAccount(id={self.id}, payment_partner_id={self.payment_partner_id}, account_name={self.account_name})"

    @property
    def is_valid(self) -> bool:
        """Vérifie si le compte de paiement a les informations nécessaires en fonction du type de partenaire de paiement."""
        if not self.is_active:
            return False
        # Ajouter d'autres types de validation selon les besoins
        return True