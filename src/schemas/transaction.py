from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator


from src.schemas.country import CountryWithMethods
from src.schemas.payment_method import PaymentTypeRead
from src.schemas.rtype import ReceivingTypeRead
from src.db.models import TransactionStatus
from src.schemas.user import UserRead


class TransactionBase(BaseModel):
    sender_country: str
    sender_currency: str
    sender_amount: int
    receiver_country: str
    receiver_currency: str
    receiver_amount: int
    conversion_rate: Decimal
    payment_method: str
    recipient_name: str
    recipient_phone: str
    receiving_method: str
    include_fee: bool
    fee_amount: int
    
    @field_serializer('sender_amount', 'receiver_amount', 'conversion_rate')
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value)




class TransactionCreate(TransactionBase):
    pass



class TransactionRead(TransactionBase):
    id: UUID
    timestamp: datetime
    status: TransactionStatus
    reference: str
    sender: UserRead


class TransactionUpdate(BaseModel):
    status: Optional[TransactionStatus] = None


class EmailSchema(BaseModel):
    email: EmailStr
    subject: str
    body: str
    


# ============================================
# TRANSFER METHODS
# ============================================

class TransferMethodsRequest(BaseModel):
    """Request schema for getting available transfer methods"""
    from_country_id: UUID
    to_country_id: UUID


class TransferMethodsResponse(BaseModel):
    """Response with available payment and receiving methods"""
    from_country: CountryWithMethods
    to_country: CountryWithMethods
    payment_methods: List[PaymentTypeRead]
    receiving_methods: List[ReceivingTypeRead]
    
    # Metadata
    can_transfer: bool = Field(
        ..., 
        description="Indicates if transfer is possible between these countries"
    )
    message: Optional[str] = Field(
        None,
        description="Additional information or restrictions"
    )


# ============================================
# TRANSFER QUOTE
# ============================================

class TransferQuoteRequest(BaseModel):
    """Request schema for calculating transfer quote"""
    from_country_id: UUID
    to_country_id: UUID
    amount: Decimal = Field(..., gt=0, description="Amount to send or receive")
    include_fee: bool = Field(
        default=False,
        description="If true, fees are included in the amount. If false, fees are added on top"
    )
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class TransferQuoteResponse(BaseModel):
    """Response with complete transfer quote calculation"""
    
    # Countries and currencies
    from_country_id: UUID
    from_country_name: str
    from_currency: str
    from_currency_symbol: str
    
    to_country_id: UUID
    to_country_name: str
    to_currency: str
    to_currency_symbol: str
    
    # Amounts
    sender_amount: float = Field(..., description="Amount sender will pay")
    receiver_amount: float = Field(..., description="Amount receiver will get")
    
    # Exchange rate
    exchange_rate: float = Field(..., description="Exchange rate applied")
    # inverse_rate: float = Field(..., description="Inverse exchange rate for display")
    
    # Fees
    fee_amount: float = Field(..., description="Fee charged for this transfer")
    fee_included: bool = Field(..., description="Whether fee is included in sender amount")
    
    # Totals
    total_to_pay: float = Field(
        ..., 
        description="Total amount sender pays (sender_amount + fee if not included)"
    )
    
    # Breakdown for display
    breakdown: dict = Field(
        ...,
        description="Detailed breakdown of calculation",
        examples=[{
            "you_send": "100.00 USD",
            "fee": "5.00 USD",
            "total_to_pay": "105.00 USD",
            "exchange_rate": "1 USD = 0.92 EUR",
            "they_receive": "92.00 EUR"
        }]
    )
    
    # Additional info
    rate_expires_at: Optional[datetime] = Field(
        None,
        description="When this quote expires (usually 30 mins)"
    )
    
    estimated_delivery: Optional[str] = Field(
        None,
        description="Estimated delivery time (e.g., 'Instant', 'Within 24 hours')"
    )


# ============================================
# TRANSFER PREVIEW
# ============================================

class TransferPreviewRequest(BaseModel):
    """Request for transfer preview with all details"""
    from_country_id: UUID
    to_country_id: UUID
    amount: Decimal = Field(..., gt=0)
    include_fee: bool = False
    payment_type_id: Optional[UUID] = Field(
        None,
        description="Selected payment method"
    )
    receiving_type_id: Optional[UUID] = Field(
        None,
        description="Selected receiving method"
    )
    recipient_name: str = Field(..., description="Nom et prénom du destinataire")
    recipient_phone: str = Field(..., description="Numéro du destinataire")



class TransferPreviewResponse(BaseModel):
    """Complete transfer preview before confirmation"""
    
     # Countries and currencies
    from_country_id: UUID
    from_country_name: str
    from_currency: str
    from_currency_symbol: str

    to_country_id: UUID
    to_country_name: str
    to_currency: str
    to_currency_symbol: str

    # Amounts
    sender_amount: float = Field(..., description="Amount sender will pay")
    receiver_amount: float = Field(..., description="Amount receiver will get")

    # Exchange rate
    exchange_rate: float = Field(..., description="Exchange rate applied")

    # Fees
    fee_value: float = Field(..., description="Fee charged for this transfer")
    fee_included: bool = Field(..., description="Whether fee is included in sender amount")

    # Totals
    total_to_pay: float = Field(
        ..., 
        description="Total amount sender pays (sender_amount + fee if not included)"
    )

    # Info destinataire
    recipient_name: str = Field(..., description="Nom & prénom du destinataire")
    recipient_phone: str = Field(..., description="Numéro de téléphone du destinataire")

    # Méthodes
    payment_method: str = Field(..., description="Méthode de paiement du sender")
    receiving_method: str = Field(..., description="Méthode de reception du destinataire")
    
    payment_instructions: PaymentInstructions

    # Breakdown for display
    breakdown: dict = Field(
        ...,
        description="Detailed breakdown of calculation",
        examples=[{
            "you_send": "100.00 USD",
            "fee": "5.00 USD",
            "total_to_pay": "105.00 USD",
            "exchange_rate": "1 USD = 0.92 EUR",
            "they_receive": "92.00 EUR"
        }]
    )

# ============================================
# TRANSFER LIMITS
# ============================================

class TransferLimits(BaseModel):
    """Transfer limits between two countries"""
    from_country_id: UUID
    to_country_id: UUID
    
    min_amount: Optional[float] = Field(
        None,
        description="Minimum transfer amount"
    )
    max_amount: Optional[float] = Field(
        None,
        description="Maximum transfer amount"
    )
    
    daily_limit: Optional[float] = Field(
        None,
        description="Maximum per day"
    )
    monthly_limit: Optional[float] = Field(
        None,
        description="Maximum per month"
    )
    
    currency: str = Field(..., description="Currency for these limits")


# ============================================
# TRANSFER ESTIMATE
# ============================================

class TransferEstimateRequest(BaseModel):
    """Quick estimate request (minimal info needed)"""
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    amount: float = Field(..., gt=0)


class TransferEstimateResponse(BaseModel):
    """Quick estimate response"""
    send_amount: float
    receive_amount: float
    exchange_rate: float
    estimated_fee: float
    total_to_pay: float
    
    # Simple display
    summary: str = Field(
        ...,
        examples=["Send 100 USD, they receive 92 EUR (fee: 5 USD)"]
    )
    

class PaymentInstructions(BaseModel):
    """Instructions for completing payment after transfer preview"""
    type: str = Field(..., description="Type of payment (e.g., 'Bank Transfer', 'Mobile Money')")
    owner_name: str = Field(..., description="Name of the account owner")
    account_number: Optional[str] = Field(
        None,
        description="Account number or phone number for payment"
    )
    phone_number: Optional[str] = Field(
        None,
        description="Phone number for payment (if applicable)"
    )



class UpdateTransactionStatus(BaseModel):
    """Seules transitions autorisées par l'admin"""
    status: TransactionStatus

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed = {
            TransactionStatus.IN_PROGRESS,
            TransactionStatus.COMPLETED,
            TransactionStatus.CANCELLED,
        }
        if v not in allowed:
            raise ValueError(f"Admin ne peut mettre que: {[s.value for s in allowed]}")
        return v
    
    
# ============================================
# SCHÉMA
# ============================================

class StatusUpdateRequest(BaseModel):
    new_status: TransactionStatus
    reason: str | None = None


class StatusUpdateResponse(BaseModel):
    transaction_id: str
    old_status: str
    new_status: str
    reference: str
    updated_at: datetime

    class Config:
        from_attributes = True


# Transitions valides
VALID_TRANSITIONS = {
    TransactionStatus.FUNDS_DEPOSITED: {
        TransactionStatus.IN_PROGRESS,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.IN_PROGRESS: {
        TransactionStatus.COMPLETED,
        TransactionStatus.CANCELLED,
    },
}