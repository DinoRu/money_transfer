"""
Package services - Exports tous les services avec logique métier
"""
from .base import BaseService

# Import des services
from src.services.user import UserService, user_service
from src.services.transaction import TransactionService, transaction_service
from src.services.transfer_quote import TransferService, transfer_service
from src.services.currency import CurrencyService, currency_service
from src.services.country import CountryService, country_service
from src.services.exchange_rate import ExchangeRateService, exchange_rate_service
from src.services.payment_partner import PaymentPartnerService, payment_partner_service
from src.services.payment_account import PaymentAccountService, payment_account_service
from src.services.fees import FeeService, fee_service

__all__ = [
    # Base
    "BaseService",
    
    # Service classes
    "UserService",
    "TransactionService",
    "TransferService",
    "CurrencyService",
    "CountryService",
    "ExchangeRateService",
    "PaymentPartnerService",
    "PaymentAccountService",
    "FeeService",
    
    # Service instances
    "user_service",
    "transaction_service",
    "transfer_service",
    "currency_service",
    "country_service",
    "exchange_rate_service",
    "payment_partner_service",
    "payment_account_service",
    "fee_service",
]