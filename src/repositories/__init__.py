"""
Package repositories - Exports tous les repositories
"""
from .base import BaseRepository

# Import des repositories
from src.repositories.user import UserRepository, user_repository
from src.repositories.currency import CurrencyRepository, currency_repository
from src.repositories.country import CountryRepository, country_repository
from src.repositories.payment_partner import PaymentPartnerRepository, payment_partner_repository
from src.repositories.payment_account import PaymentAccountRepository, payment_account_repository
from src.repositories.transfer import TransactionRepository, transaction_repository
from .fee import FeeRepository, fee_repository
# from .fcm_token import FCMTokenRepository, fcm_token_repository
from src.repositories.exchange_rate import ExchangeRateRepository, exchange_rate_repository

__all__ = [
    # Base
    "BaseRepository",
    
    # Repository classes
    "UserRepository",
    "CurrencyRepository",
    "CountryRepository",
    "PaymentPartnerRepository",
    "PaymentAccountRepository",
    "TransactionRepository",
    "FeeRepository",
    "FCMTokenRepository",
    "ExchangeRateRepository",
    
    # Repository instances
    "user_repository",
    "currency_repository",
    "country_repository",
    "payment_partner_repository",
    "payment_account_repository",
    "transaction_repository",
    "fee_repository",
    # "fcm_token_repository",
    "exchange_rate_repository"
]