"""
Schemas pour le modèle Country
"""
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, IDMixin
from src.schemas.currency import CurrencyResponse


class CountryCreate(BaseSchema):
    """Schema pour créer un pays"""
    name: str = Field(..., min_length=2, max_length=100, description="Nom du pays")
    code: str = Field(..., min_length=2, max_length=2, description="Code pays ISO 3166-1 alpha-2")
    currency_id: UUID = Field(..., description="ID de la devise associée")
    dial_code: str = Field(..., pattern=r'^\+\d{1,4}$', description="Indicatif téléphonique (ex: +33)")
    flag: str = Field(..., min_length=1, max_length=10, description="Emoji du drapeau")
    phone_number_length: int = Field(default=9, ge=7, le=15, description="Longueur du numéro de téléphone")
    phone_format_example: Optional[str] = Field(None, max_length=20, description="Exemple de format de numéro")
    can_send_from: bool = Field(default=True, description="Peut envoyer de l'argent depuis ce pays")
    can_send_to: bool = Field(default=True, description="Peut recevoir de l'argent vers ce pays")


class CountryUpdate(BaseSchema):
    """Schema pour mettre à jour un pays"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    currency_id: Optional[UUID] = None
    dial_code: Optional[str] = Field(None, pattern=r'^\+\d{1,4}$')
    flag: Optional[str] = Field(None, min_length=1, max_length=10)
    phone_number_length: Optional[int] = Field(None, ge=7, le=15)
    phone_format_example: Optional[str] = Field(None, max_length=20)
    can_send_from: Optional[bool] = None
    can_send_to: Optional[bool] = None


class CountryResponse(BaseSchema, IDMixin):
    """Schema de réponse pour un pays"""
    name: str
    code: str
    currency_id: UUID
    dial_code: str
    flag: str
    phone_number_length: int
    phone_format_example: Optional[str] = None
    can_send_from: bool
    can_send_to: bool


class CountryWithCurrency(CountryResponse):
    """Schema de réponse avec les détails de la devise"""
    currency: CurrencyResponse

    @property
    def display_name(self) -> str:
        return f"{self.flag} ({self.name})"

    @property
    def currency_code(self) -> str:
        return self.currency.code