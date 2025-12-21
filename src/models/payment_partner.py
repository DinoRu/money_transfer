"""
Modèle PaymentPartner
"""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, VARCHAR
from sqlalchemy.orm import relationship

from .base import Base, BaseModel
from .enums import PaymentPartnerType



class PaymentPartner(BaseModel):
    __tablename__ = "payment_partners"

    name = Column(VARCHAR(100), nullable=False, unique=True)
    country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    type = Column(VARCHAR(50), nullable=False)
    description = Column(VARCHAR(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    can_send = Column(Boolean, nullable=False, server_default='true')
    can_receive = Column(Boolean, nullable=False, server_default='true')

    # Relations
    country = relationship("Country", back_populates="payment_partners", lazy="selectin")
    payment_accounts = relationship("PaymentAccount", back_populates="payment_partner", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"PaymentPartner(id={self.id}, name={self.name}, type={self.type})"