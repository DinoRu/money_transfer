"""
Schémas pour les devises
"""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict

from src.models.base import TimestampMixin
from src.schemas.base import IDMixin



# ==================== Schémas de Base ====================

class CurrencyBase(BaseModel):
    """Schéma de base pour une devise"""
    code: str = Field(..., min_length=3, max_length=3, description="Code ISO 4217")
    name: str = Field(..., min_length=2, max_length=100, description="Nom de la devise")
    symbol: str = Field(..., max_length=10, description="Symbole de la devise")
    description: Optional[str] = Field(None, description="Description")
    decimal_places: int = Field(0, ge=0, le=8, description="Nombre de décimales")
    display_order: int = Field(0, ge=0, description="Ordre d'affichage")
    
    
    model_config = ConfigDict(from_attributes=True)


class CurrencyCreate(CurrencyBase):
    """Schéma pour créer une devise"""
    is_active: bool = Field(True, description="Devise active")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "XOF",
                "name": "West African CFA Franc",
                "symbol": "F CFA",
                "description": "Franc CFA de la zone BCEAO",
                "decimal_places": 0,
                "display_order": 1,
                "is_active": True
            }
        }
    )


class CurrencyUpdate(BaseModel):
    """Schéma pour mettre à jour une devise"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    symbol: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    decimal_places: Optional[int] = Field(None, ge=0, le=8)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name_fr": "Franc CFA (Zone BCEAO)",
                "description": "Devise de la zone BCEAO",
                "display_order": 2
            }
        }
    )


class CurrencyResponse(CurrencyBase, IDMixin, TimestampMixin):
    """Schéma de réponse pour une devise"""
    is_active: bool = Field(..., description="Devise active")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3f1a2b3c-4d5e-6f7g-8h9i-j10k11l12m13",
                "code": "XOF",
                "name": "West African CFA Franc",
                "symbol": "F CFA",
                "description": "Franc CFA de la zone BCEAO",
                "decimal_places": 0,
                "display_order": 1,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class CurrencyListResponse(BaseModel):
    """Schéma de réponse simplifié pour une liste de devises"""
    id: UUID
    code: str
    symbol: str
    is_active: bool
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3f1a2b3c-4d5e-6f7g-8h9i-j10k11l12m13",
                "code": "XOF",
                "name_fr": "Franc CFA (BCEAO)",
                "symbol": "F CFA",
                "is_active": True
            }
        }
    )


class CurrencyWithCountriesResponse(CurrencyResponse):
    """Devise avec la liste des pays"""
    country_count: Optional[int] = Field(None, description="Nombre de pays")
    
    model_config = ConfigDict(from_attributes=True)