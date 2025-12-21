"""
Schemas pour le modèle Fee
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from src.models.enums import FeeType
from .base import BaseSchema, IDMixin, TimestampMixin
from src.schemas.country import CountryResponse


class FeeCreate(BaseSchema):
    """Schema pour créer des frais"""
    from_country_id: UUID = Field(..., description="ID du pays source")
    to_country_id: UUID = Field(..., description="ID du pays destination")
    fee_type: FeeType = Field(..., description="Type de frais")
    fee_value: Decimal = Field(..., gt=0, description="Valeur du frais")
    min_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Montant minimum")
    max_amount: Optional[Decimal] = Field(None, ge=0, description="Montant maximum")
    is_active: bool = Field(default=True, description="Indique si le frais est actif")


class FeeUpdate(BaseSchema):
    """Schema pour mettre à jour des frais"""
    from_country_id: Optional[UUID] = None
    to_country_id: Optional[UUID] = None
    fee_type: Optional[FeeType] = None
    fee_value: Optional[Decimal] = Field(None, gt=0)
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class FeeResponse(BaseSchema, IDMixin, TimestampMixin):
    """Schema de réponse pour des frais"""
    from_country_id: UUID
    to_country_id: UUID
    fee_type: FeeType
    fee_value: Decimal
    min_amount: Decimal
    max_amount: Optional[Decimal] = None
    is_active: bool


class FeeWithCountries(FeeResponse):
    """Schema de réponse avec les détails des pays"""
    from_country: CountryResponse
    to_country: CountryResponse

    @property
    def corridor(self) -> str:
        """Retourne le corridor sous forme de chaîne"""
        return f"{self.from_country.name}-{self.to_country.name}"

    @property
    def display_name(self) -> str:
        """Nom d'affichage du frais"""
        fee_desc = f"{self.fee_value}%" if self.fee_type == FeeType.PERCENTAGE else f"{self.fee_value}"
        return f"{self.from_country.name} → {self.to_country.name}: {fee_desc} ({self.fee_type.value})"


class FeeCalculation(BaseSchema):
    """Schema pour calculer les frais d'un transfert"""
    from_country_id: UUID = Field(..., description="ID du pays source")
    to_country_id: UUID = Field(..., description="ID du pays destination")
    amount: Decimal = Field(..., gt=0, description="Montant du transfert")


class FeeCalculationResponse(BaseSchema):
    """Schema de réponse pour le calcul des frais"""
    from_country: CountryResponse
    to_country: CountryResponse
    amount: Decimal
    fee_type: FeeType
    fee_value: Decimal
    calculated_fee: Decimal
    total_amount: Decimal