"""
Schemas pour le modèle ExchangeRate
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import BaseSchema, IDMixin, TimestampMixin
from src.schemas.currency import CurrencyResponse


class ExchangeRateCreate(BaseSchema):
    """Schema pour créer un taux de change"""
    from_currency_id: UUID = Field(..., description="ID de la devise source")
    to_currency_id: UUID = Field(..., description="ID de la devise cible")
    rate: float = Field(..., gt=0, description="Taux de change (combien de to_currency pour 1 from_currency)")
    is_active: bool = Field(default=True, description="Indique si le taux est actif")

    @field_validator('rate')
    @classmethod
    def validate_rate(cls, v: float) -> float:
        """Valide que le taux est positif"""
        if v <= 0:
            raise ValueError("Le taux de change doit être positif")
        return v


class ExchangeRateUpdate(BaseSchema):
    """Schema pour mettre à jour un taux de change"""
    rate: Optional[float] = Field(None, gt=0, description="Nouveau taux de change")
    is_active: Optional[bool] = Field(None, description="Activer/désactiver le taux")


class ExchangeRateResponse(BaseSchema, IDMixin, TimestampMixin):
    """Schema de réponse pour un taux de change"""
    from_currency_id: UUID
    to_currency_id: UUID
    rate: Decimal
    is_active: bool


class ExchangeRateWithCurrencies(ExchangeRateResponse):
    """Schema de réponse avec les détails des devises"""
    from_currency: CurrencyResponse
    to_currency: CurrencyResponse

    @property
    def corridor(self) -> str:
        """Retourne le corridor sous forme de chaîne"""
        return f"{self.from_currency.code}-{self.to_currency.code}"

    @property
    def display_name(self) -> str:
        """Nom d'affichage du taux"""
        return f"1 {self.from_currency.code} = {self.rate} {self.to_currency.code}"


class ExchangeRateQuery(BaseSchema):
    """Schema pour rechercher un taux de change"""
    from_currency_id: Optional[UUID] = Field(None, description="ID de la devise source")
    to_currency_id: Optional[UUID] = Field(None, description="ID de la devise cible")


class ExchangeRateConversion(BaseSchema):
    """Schema pour convertir un montant"""
    from_currency_id: UUID = Field(..., description="ID de la devise source")
    to_currency_id: UUID = Field(..., description="ID de la devise cible")
    amount: float = Field(..., gt=0, description="Montant à convertir")


class ExchangeRateConversionResponse(BaseSchema):
    """Schema de réponse pour une conversion"""
    from_currency: CurrencyResponse
    to_currency: CurrencyResponse
    rate: Decimal
    original_amount: float
    converted_amount: float
