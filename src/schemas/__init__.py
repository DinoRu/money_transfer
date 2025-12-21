"""
Package schemas - Exports tous les schemas Pydantic
"""
from .base import BaseSchema, TimestampMixin, IDMixin

# User schemas
from src.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserWithToken,
    UserLogin, UserLoginResponse
)

# Currency schemas
from src.schemas.currency import (
    CurrencyCreate, CurrencyUpdate, CurrencyResponse
)

# Country schemas
from src.schemas.country import (
    CountryCreate, CountryUpdate, CountryResponse, CountryWithCurrency
)

# Payment Partner schemas
from src.schemas.payment_partner import (
    PaymentPartnerCreate, PaymentPartnerUpdate,
    PaymentPartnerResponse, PaymentPartnerWithCountry
)

# Payment Account schemas
from src.schemas.payment_account import (
    PaymentAccountCreate, PaymentAccountUpdate,
    PaymentAccountResponse, PaymentAccountWithPartner
)

# Transaction schemas
from src.schemas.transfer import (
    TransferCreate, TransferUpdate, TransferResponse,
    TransferWithSender, TransferStatusUpdate, TransferFilter
)

# Fee schemas
from src.schemas.fees import (
    FeeCreate, FeeUpdate, FeeResponse,
    FeeWithCountries, FeeCalculation, FeeCalculationResponse
)

# FCM Token schemas
# from .fcm_token import (
#     FCMTokenCreate, FCMTokenUpdate, FCMTokenResponse
# )

# Exchange Rate schemas
from src.schemas.exchange_rate import (
    ExchangeRateCreate, ExchangeRateUpdate, ExchangeRateResponse,
    ExchangeRateWithCurrencies, ExchangeRateQuery, 
    ExchangeRateConversion, ExchangeRateConversionResponse
)

# Transfer schemas
from src.schemas.transfer import (
    TransferQuoteRequest, TransferQuoteResponse, TransferCalculation
)

__all__ = [
    # Base
    "BaseSchema", "TimestampMixin", "IDMixin",
    
    # User
    "UserCreate", "UserUpdate", "UserResponse", "UserWithToken",
    "UserLogin", "UserLoginResponse",
    
    # Currency
    "CurrencyCreate", "CurrencyUpdate", "CurrencyResponse",
    
    # Country
    "CountryCreate", "CountryUpdate", "CountryResponse", "CountryWithCurrency",
    
    # Payment Partner
    "PaymentPartnerCreate", "PaymentPartnerUpdate",
    "PaymentPartnerResponse", "PaymentPartnerWithCountry",
    
    # Payment Account
    "PaymentAccountCreate", "PaymentAccountUpdate",
    "PaymentAccountResponse", "PaymentAccountWithPartner",
    
    # Transfer
    "TransferCreate", "TransferUpdate", "TransferResponse",
    "TransferWithSender", "TransferStatusUpdate", "TransferFilter",
    
    # Fee
    "FeeCreate", "FeeUpdate", "FeeResponse",
    "FeeWithCountries", "FeeCalculation", "FeeCalculationResponse",
    
    # FCM Token
    # "FCMTokenCreate", "FCMTokenUpdate", "FCMTokenResponse",
    
    # Exchange Rate
    "ExchangeRateCreate", "ExchangeRateUpdate", "ExchangeRateResponse",
    "ExchangeRateWithCurrencies", "ExchangeRateQuery", 
    "ExchangeRateConversion", "ExchangeRateConversionResponse",
    
    # Transfer
    "TransferQuoteRequest", "TransferQuoteResponse", "TransferCalculation",
]