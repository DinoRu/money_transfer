from decimal import Decimal
from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator, model_validator
from enum import Enum


# Enum pour le type de conversion
class ConversionType(str, Enum):
    SEND = "send"  # L'utilisateur spécifie le montant à envoyer
    RECEIVE = "receive"  # L'utilisateur spécifie le montant à recevoir


# Schéma pour la création d'un taux de change
class CreateExchangeRate(BaseModel):
    from_currency_id: UUID
    to_currency_id: UUID
    rate: Decimal

    @field_validator('rate')
    @classmethod
    def validate_rate(cls, v):
        if v <= 0:
            raise ValueError("Le taux de change doit être positif")
        return v


# Schéma pour la mise à jour d'un taux de change
class UpdateExchangeRate(BaseModel):
    from_currency_id: Optional[UUID] = None
    to_currency_id: Optional[UUID] = None
    rate: Optional[Decimal] = None

    @field_validator('rate')
    @classmethod
    def validate_rate(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Le taux de change doit être positif")
        return v


# Schéma pour lire un taux de change
class ExchangeRateRead(BaseModel):
    id: UUID
    from_currency_id: UUID
    to_currency_id: UUID
    rate: Decimal
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Schéma pour la requête de conversion (FLEXIBLE)
class ConversionRequest(BaseModel):
    from_currency: str  # Code de la devise source (ex: "USD")
    to_currency: str    # Code de la devise cible (ex: "EUR")
    send_amount: Optional[Decimal] = None      # Montant à envoyer
    receive_amount: Optional[Decimal] = None   # Montant à recevoir

    @field_validator('from_currency', 'to_currency')
    @classmethod
    def validate_currency_code(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Le code de devise ne peut pas être vide")
        return v.upper().strip()

    @field_validator('send_amount', 'receive_amount')
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Le montant doit être positif")
        return v

    @model_validator(mode='after')
    def validate_amounts(self):
        """Vérifie qu'exactement un montant est fourni"""
        if self.send_amount is None and self.receive_amount is None:
            raise ValueError("Vous devez fournir soit 'send_amount' soit 'receive_amount'")
        
        if self.send_amount is not None and self.receive_amount is not None:
            raise ValueError("Vous ne pouvez fournir qu'un seul montant: 'send_amount' OU 'receive_amount'")
        
        return self


# Schéma alternatif avec query parameters (pour GET)
class ConversionQueryParams(BaseModel):
    from_currency: str
    to_currency: str
    send_amount: Optional[Decimal] = None
    receive_amount: Optional[Decimal] = None

    class Config:
        # Permet la validation même avec des query params
        str_strip_whitespace = True


# Schéma pour la réponse de conversion
class ConversionResponse(BaseModel):
    from_currency: str
    to_currency: str
    send_amount: Decimal       # Montant envoyé
    receive_amount: Decimal    # Montant reçu
    exchange_rate: Decimal     # Taux de change utilisé
    conversion_type: ConversionType  # Type de conversion effectuée
    timestamp: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "from_currency": "USD",
                "to_currency": "EUR",
                "send_amount": 100.00,
                "receive_amount": 92.50,
                "exchange_rate": 0.925,
                "conversion_type": "send",
                "timestamp": "2024-01-15T10:30:00"
            }
        }


# Schéma pour les erreurs de conversion
class ConversionError(BaseModel):
    error: str
    detail: str
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "CURRENCY_NOT_FOUND",
                "detail": "La devise USD n'existe pas",
                "error_code": "ERR_404"
            }
        }


# Schéma pour obtenir le taux de change actuel (sans conversion)
class ExchangeRateQuery(BaseModel):
    from_currency: str
    to_currency: str

    @field_validator('from_currency', 'to_currency')
    @classmethod
    def validate_currency_code(cls, v):
        return v.upper().strip()


# Schéma pour la réponse du taux de change
class ExchangeRateResponse(BaseModel):
    from_currency: str
    to_currency: str
    rate: Decimal
    inverse_rate: Decimal  # Taux inverse (utile pour l'app Flutter)
    last_updated: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "from_currency": "USD",
                "to_currency": "EUR",
                "rate": 0.925,
                "inverse_rate": 1.081,
                "last_updated": "2024-01-15T10:30:00"
            }
        }


# Schéma pour une liste de conversions favorites (pour Flutter)
class FavoriteConversion(BaseModel):
    id: Optional[str] = None
    from_currency: str
    to_currency: str
    label: Optional[str] = None  # Ex: "USD vers EUR"
    is_default: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "id": "fav-1",
                "from_currency": "USD",
                "to_currency": "EUR",
                "label": "Dollar vers Euro",
                "is_default": True
            }
        }