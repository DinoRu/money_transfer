"""
Schemas pour le modèle PaymentPartner
"""
from typing import Optional
from uuid import UUID

from pydantic import Field

from src.models.enums import PaymentPartnerType
from .base import BaseSchema, IDMixin
from src.schemas.country import CountryResponse


class PaymentPartnerCreate(BaseSchema):
    """Schema pour créer un partenaire de paiement"""
    name: str = Field(..., min_length=2, max_length=100, description="Nom du partenaire")
    country_id: UUID = Field(..., description="ID du pays associé")
    type: PaymentPartnerType = Field(..., description="Type de méthode de paiement")
    description: Optional[str] = Field(None, max_length=255, description="Description du partenaire")
    is_active: bool = Field(default=True, description="Indique si le partenaire est actif")
    can_send: bool = Field(default=True, description="Peut être utilisé pour envoyer")
    can_receive: bool = Field(default=True, description="Peut être utilisé pour recevoir")


class PaymentPartnerUpdate(BaseSchema):
    """Schema pour mettre à jour un partenaire de paiement"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    country_id: Optional[UUID] = None
    type: Optional[PaymentPartnerType] = None
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    can_send: Optional[bool] = None
    can_receive: Optional[bool] = None


class PaymentPartnerResponse(BaseSchema, IDMixin):
    """Schema de réponse pour un partenaire de paiement"""
    name: str
    country_id: UUID
    type: PaymentPartnerType
    description: Optional[str] = None
    is_active: bool
    can_send: bool
    can_receive: bool


class PaymentPartnerWithCountry(PaymentPartnerResponse):
    """Schema de réponse avec les détails du pays"""
    country: CountryResponse