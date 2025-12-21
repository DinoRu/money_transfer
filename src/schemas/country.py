from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator, Field
from uuid import UUID

from src.schemas.currency import CurrencyModel

# ============================================
# COUNTRY SCHEMAS
# ============================================

class CountryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code_iso: str = Field(..., min_length=2, max_length=3, description="ISO country code (e.g., US, FR)")
    flag_url: Optional[str] = None
    
    @field_validator('code_iso')
    @classmethod
    def validate_code_iso(cls, v):
        return v.upper().strip()


class CountryCreate(CountryBase):
    """Schema for creating a new country"""
    currency_id: UUID


class CountryUpdate(BaseModel):
    """Schema for updating a country (all fields optional)"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    code_iso: Optional[str] = Field(None, min_length=2, max_length=3)
    currency_id: Optional[UUID] = None
    flag_url: Optional[str] = None
    
    @field_validator('code_iso')
    @classmethod
    def validate_code_iso(cls, v):
        if v is not None:
            return v.upper().strip()
        return v


class CountryModel(CountryBase):
    """Schema for reading country data with relations"""
    id: UUID
    currency_id: UUID
    currency: Optional[CurrencyModel] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CountrySimple(BaseModel):
    """Simplified country schema without relations"""
    id: UUID
    name: str
    code_iso: str
    flag_url: Optional[str] = None

    class Config:
        from_attributes = True


class CountryList(BaseModel):
    """Schema for list of countries with metadata"""
    total: int
    countries: List[CountryModel]


