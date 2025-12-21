"""
Schemas pour le modèle PaymentAccount
"""
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, IDMixin
from src.schemas.payment_partner import PaymentPartnerResponse


class PaymentAccountCreate(BaseSchema):
    """Schema pour créer un compte de paiement"""
    payment_partner_id: UUID = Field(..., description="ID du partenaire de paiement")
    account_name: str = Field(..., min_length=2, max_length=100, description="Nom du compte")
    account_number: Optional[str] = Field(None, max_length=20, description="Numéro de compte")
    bank_name: Optional[str] = Field(None, max_length=100, description="Nom de la banque")
    is_active: bool = Field(default=True, description="Indique si le compte est actif")


class PaymentAccountUpdate(BaseSchema):
    """Schema pour mettre à jour un compte de paiement"""
    payment_partner_id: Optional[UUID] = None
    account_name: Optional[str] = Field(None, min_length=2, max_length=100)
    account_number: Optional[str] = Field(None, max_length=20)
    bank_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class PaymentAccountResponse(BaseSchema, IDMixin):
    """Schema de réponse pour un compte de paiement"""
    payment_partner_id: UUID
    account_name: str
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    is_active: bool


class PaymentAccountWithPartner(PaymentAccountResponse):
    """Schema de réponse avec les détails du partenaire"""
    payment_partner: PaymentPartnerResponse