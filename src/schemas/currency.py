from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator, Field
from uuid import UUID


# ============================================
# CURRENCY SCHEMAS
# ============================================

class CurrencyBase(BaseModel):
    code: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code (e.g., USD, EUR)")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        return v.upper().strip()


class CurrencyCreate(CurrencyBase):
    """Schema for creating a new currency"""
    pass


class CurrencyUpdate(BaseModel):
    """Schema for updating a currency (all fields optional)"""
    code: Optional[str] = Field(None, min_length=3, max_length=3)
    name: Optional[str] = None
    symbol: Optional[str] = None
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        if v is not None:
            return v.upper().strip()
        return v


class CurrencyModel(BaseModel):
    """Schema for reading currency data"""
    id: UUID
    code: str
    name: str
    symbol: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CurrencyList(BaseModel):
    """Schema for list of currencies with metadata"""
    total: int
    currencies: List[CurrencyModel]

