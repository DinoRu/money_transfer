from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator, Field
from uuid import UUID

# ============================================
# COMMON SCHEMAS
# ============================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Generic error response"""
    detail: str
    error_code: Optional[str] = None


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operations"""
    message: str
    deleted_count: int
    success: bool = True


# ============================================
# QUERY PARAMETER SCHEMAS
# ============================================

class CurrencySearchParams(BaseModel):
    """Query parameters for searching currencies"""
    search: Optional[str] = Field(None, description="Search by code or name")
    code: Optional[str] = Field(None, min_length=3, max_length=3)
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class CountrySearchParams(BaseModel):
    """Query parameters for searching countries"""
    search: Optional[str] = Field(None, description="Search by name or code")
    code_iso: Optional[str] = Field(None, min_length=2, max_length=3)
    currency_id: Optional[UUID] = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class FeeSearchParams(BaseModel):
    """Query parameters for searching fees"""
    from_country_id: Optional[UUID] = None
    to_country_id: Optional[UUID] = None
    fee_type: Optional[str] = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)