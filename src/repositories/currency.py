"""
Repository pour les devises en mode asynchrone
"""
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Currency
from .base import BaseRepository


class CurrencyRepository(BaseRepository[Currency]):
    """Repository pour les opérations sur les devises"""
    
    def __init__(self):
        super().__init__(Currency)
    
    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Currency]:
        """
        Récupère une devise par son code ISO
        
        Args:
            db: Session asynchrone
            code: Code ISO de la devise (ex: EUR, USD)
            
        Returns:
            La devise trouvée ou None
        """
        result = await db.execute(
            select(Currency).where(Currency.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_active_currencies(self, db: AsyncSession) -> List[Currency]:
        """
        Récupère toutes les devises actives
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des devises actives
        """
        result = await db.execute(
            select(Currency).where(Currency.is_active == True)
        )
        return list(result.scalars().all())
    
    async def activate(self, db: AsyncSession, currency_id: UUID) -> Optional[Currency]:
        """
        Active une devise
        
        Args:
            db: Session asynchrone
            currency_id: UUID de la devise
            
        Returns:
            La devise activée ou None
        """
        currency = await self.get(db, currency_id)
        if currency:
            currency.is_active = True
            await db.flush()
            await db.refresh(currency)
        return currency
    
    async def deactivate(self, db: AsyncSession, currency_id: UUID) -> Optional[Currency]:
        """
        Désactive une devise
        
        Args:
            db: Session asynchrone
            currency_id: UUID de la devise
            
        Returns:
            La devise désactivée ou None
        """
        currency = await self.get(db, currency_id)
        if currency:
            currency.is_active = False
            await db.flush()
            await db.refresh(currency)
        return currency


# Instance globale du repository
currency_repository = CurrencyRepository()