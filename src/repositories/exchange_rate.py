"""
Repository pour le modèle ExchangeRate en mode asynchrone
"""
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import ExchangeRate
from .base import BaseRepository


class ExchangeRateRepository(BaseRepository[ExchangeRate]):
    """Repository pour gérer les taux de change"""
    
    def __init__(self):
        super().__init__(ExchangeRate)
    
    async def get_by_currencies(
        self,
        db: AsyncSession,
        from_currency_id: UUID,
        to_currency_id: UUID
    ) -> Optional[ExchangeRate]:
        """
        Récupère le taux de change entre deux devises
        
        Args:
            db: Session asynchrone
            from_currency_id: UUID de la devise source
            to_currency_id: UUID de la devise cible
            
        Returns:
            Le taux de change ou None
        """
        result = await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.from_currency_id == from_currency_id,
                ExchangeRate.to_currency_id == to_currency_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_with_currencies(
        self,
        db: AsyncSession,
        rate_id: UUID
    ) -> Optional[ExchangeRate]:
        """
        Récupère un taux avec les devises chargées
        
        Args:
            db: Session asynchrone
            rate_id: UUID du taux
            
        Returns:
            Le taux avec devises ou None
        """
        result = await db.execute(
            select(ExchangeRate)
            .options(
                selectinload(ExchangeRate.from_currency),
                selectinload(ExchangeRate.to_currency)
            )
            .where(ExchangeRate.id == rate_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_with_currencies(self, db: AsyncSession) -> List[ExchangeRate]:
        """
        Récupère tous les taux avec devises
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des taux avec devises
        """
        result = await db.execute(
            select(ExchangeRate).options(
                selectinload(ExchangeRate.from_currency),
                selectinload(ExchangeRate.to_currency)
            )
        )
        return list(result.scalars().all())
    
    async def get_active_rates(self, db: AsyncSession) -> List[ExchangeRate]:
        """
        Récupère les taux de change actifs
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des taux actifs
        """
        result = await db.execute(
            select(ExchangeRate).where(ExchangeRate.is_active == True)
        )
        return list(result.scalars().all())
    
    async def get_by_from_currency(
        self,
        db: AsyncSession,
        currency_id: UUID
    ) -> List[ExchangeRate]:
        """
        Récupère les taux depuis une devise
        
        Args:
            db: Session asynchrone
            currency_id: UUID de la devise source
            
        Returns:
            Liste des taux
        """
        result = await db.execute(
            select(ExchangeRate)
            .options(selectinload(ExchangeRate.to_currency))
            .where(ExchangeRate.from_currency_id == currency_id)
        )
        return list(result.scalars().all())
    
    async def get_by_to_currency(
        self,
        db: AsyncSession,
        currency_id: UUID
    ) -> List[ExchangeRate]:
        """
        Récupère les taux vers une devise
        
        Args:
            db: Session asynchrone
            currency_id: UUID de la devise cible
            
        Returns:
            Liste des taux
        """
        result = await db.execute(
            select(ExchangeRate)
            .options(selectinload(ExchangeRate.from_currency))
            .where(ExchangeRate.to_currency_id == currency_id)
        )
        return list(result.scalars().all())
    
    async def activate(self, db: AsyncSession, rate_id: UUID) -> Optional[ExchangeRate]:
        """
        Active un taux de change
        
        Args:
            db: Session asynchrone
            rate_id: UUID du taux
            
        Returns:
            Le taux activé ou None
        """
        rate = await self.get(db, rate_id)
        if rate:
            rate.is_active = True
            await db.flush()
            await db.refresh(rate)
        return rate
    
    async def deactivate(self, db: AsyncSession, rate_id: UUID) -> Optional[ExchangeRate]:
        """
        Désactive un taux de change
        
        Args:
            db: Session asynchrone
            rate_id: UUID du taux
            
        Returns:
            Le taux désactivé ou None
        """
        rate = await self.get(db, rate_id)
        if rate:
            rate.is_active = False
            await db.flush()
            await db.refresh(rate)
        return rate


# Instance globale du repository
exchange_rate_repository = ExchangeRateRepository()