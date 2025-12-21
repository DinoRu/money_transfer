from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator, Field
from uuid import UUID

from src.schemas.country import CountrySimple

# ============================================
# FEE SCHEMAS
# ============================================

class FeeBase(BaseModel):
    fee: Decimal = Field(..., gt=0, description="Fee amount (must be positive)")
    
    @field_validator('fee')
    @classmethod
    def validate_fee(cls, v, info):
        if v <= 0:
            raise ValueError("Fee must be positive")
        # If percentage, ensure it's reasonable (0-100)
        
        return v


class FeeCreate(FeeBase):
    """Schema for creating a new fee"""
    from_country_id: UUID
    to_country_id: UUID
    min_amount: Optional[Decimal] = Field(None, ge=0, description="Minimum transaction amount for this fee")
    max_amount: Optional[Decimal] = Field(None, gt=0, description="Maximum transaction amount for this fee")


class FeeUpdate(BaseModel):
    """Schema for updating a fee (all fields optional)"""
    fee: Optional[Decimal] = Field(None, gt=0)
    from_country_id: Optional[UUID] = None
    to_country_id: Optional[UUID] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, gt=0)
    


class FeeView(BaseModel):
    """Schema for reading fee data"""
    id: UUID
    from_country_id: UUID
    to_country_id: UUID
    fee: Decimal
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FeeWithCountries(FeeView):
    """Schema for fee with country details"""
    from_country: Optional[CountrySimple] = None
    to_country: Optional[CountrySimple] = None


class FeeCalculationRequest(BaseModel):
    """Schema for calculating fees"""
    from_country_id: UUID
    to_country_id: UUID
    amount: Decimal = Field(..., gt=0, description="Transaction amount")


class FeeCalculationResponse(BaseModel):
    """Schema for fee calculation response"""
    from_country_id: UUID
    to_country_id: UUID
    amount: Decimal
    fee_amount: Decimal
    total_amount: Decimal  # amount + fee
    fee_percentage: Optional[Decimal] = None  # For display purposes


class FeeList(BaseModel):
    """Schema for list of fees with metadata"""
    total: int
    fees: List[FeeWithCountries]