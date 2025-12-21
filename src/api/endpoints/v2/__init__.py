"""
Package routers - Exports tous les routers de l'API
"""
from .auth import router as auth_router
from .currency import router as currency_router
from .country import router as country_router
from .exchange_rate import router as exchange_rate_router
from .payment_partner import router as payment_partner_router
from .payment_account import router as payment_account_router
from .fee import router as fee_router
from .user import router as user_router


__all__ = [
    "auth_router",
    "currency_router",
    "country_router",
    "exchange_rate_router",
    "payment_partner_router",
    "payment_account_router",
    "fee_router",
    "user_router",
]