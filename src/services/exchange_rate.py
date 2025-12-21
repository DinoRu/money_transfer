"""
Service pour les taux de change en mode asynchrone
"""
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ExchangeRate
from src.repositories import exchange_rate_repository
from src.schemas.exchange_rate import (
    ExchangeRateCreate, ExchangeRateUpdate, ExchangeRateResponse,
    ExchangeRateWithCurrencies, ExchangeRateConversion, ExchangeRateConversionResponse
)
from .base import BaseService


class ExchangeRateService(BaseService[ExchangeRate, ExchangeRateCreate, ExchangeRateUpdate, ExchangeRateResponse]):
    """Service pour la gestion des taux de change"""
    
    def __init__(self):
        super().__init__(exchange_rate_repository, ExchangeRateResponse)
    
    async def get_by_currencies(
        self,
        db: AsyncSession,
        from_currency_id: UUID,
        to_currency_id: UUID
    ) -> Optional[ExchangeRateWithCurrencies]:
        """Récupère le taux entre deux devises"""
        rate = await self.repository.get_by_currencies(db, from_currency_id, to_currency_id)
        if rate:
            return ExchangeRateWithCurrencies.model_validate(
                await self.repository.get_with_currencies(db, rate.id)
            )
        return None
    
    async def get_with_currencies(self, db: AsyncSession, rate_id: UUID) -> Optional[ExchangeRateWithCurrencies]:
        """Récupère un taux avec devises"""
        rate = await self.repository.get_with_currencies(db, rate_id)
        if rate:
            return ExchangeRateWithCurrencies.model_validate(rate)
        return None
    
    async def get_all_with_currencies(self, db: AsyncSession) -> List[ExchangeRateWithCurrencies]:
        """Récupère tous les taux avec devises"""
        rates = await self.repository.get_all_with_currencies(db)
        return [ExchangeRateWithCurrencies.model_validate(r) for r in rates]
    
    async def convert_amount(
        self,
        db: AsyncSession,
        conversion: ExchangeRateConversion
    ) -> ExchangeRateConversionResponse:
        """Convertit un montant"""
        rate = await self.repository.get_by_currencies(
            db, conversion.from_currency_id, conversion.to_currency_id
        )
        
        if not rate:
            raise ValueError("Taux de change non disponible")
        
        if not rate.is_active:
            raise ValueError("Taux de change inactif")
        
        converted_amount = conversion.amount * rate.rate
        
        rate_full = await self.repository.get_with_currencies(db, rate.id)
        
        return ExchangeRateConversionResponse(
            from_currency=rate_full.from_currency,
            to_currency=rate_full.to_currency,
            rate=rate.rate,
            original_amount=conversion.amount,
            converted_amount=converted_amount
        )


# Instance globale
exchange_rate_service = ExchangeRateService()