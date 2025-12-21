"""
Repository pour le modèle Fee en mode asynchrone
"""
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Fee
from src.models.enums import FeeType
from .base import BaseRepository


class FeeRepository(BaseRepository[Fee]):
    """Repository pour gérer les frais"""
    
    def __init__(self):
        super().__init__(Fee)
    
    async def get_with_countries(self, db: AsyncSession, fee_id: UUID) -> Optional[Fee]:
        """
        Récupère un frais avec les pays chargés
        
        Args:
            db: Session asynchrone
            fee_id: UUID du frais
            
        Returns:
            Le frais avec pays ou None
        """
        result = await db.execute(
            select(Fee)
            .options(
                selectinload(Fee.from_country),
                selectinload(Fee.to_country)
            )
            .where(Fee.id == fee_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_with_countries(self, db: AsyncSession) -> List[Fee]:
        """
        Récupère tous les frais avec pays
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des frais avec pays
        """
        result = await db.execute(
            select(Fee).options(
                selectinload(Fee.from_country),
                selectinload(Fee.to_country)
            )
        )
        return list(result.scalars().all())
    
    async def get_by_corridor(
        self,
        db: AsyncSession,
        from_country_id: UUID,
        to_country_id: UUID
    ) -> List[Fee]:
        """
        Récupère les frais pour un corridor
        
        Args:
            db: Session asynchrone
            from_country_id: UUID du pays source
            to_country_id: UUID du pays destination
            
        Returns:
            Liste des frais
        """
        result = await db.execute(
            select(Fee)
            .options(
                selectinload(Fee.from_country),
                selectinload(Fee.to_country)
            )
            .where(
                Fee.from_country_id == from_country_id,
                Fee.to_country_id == to_country_id
            )
        )
        return list(result.scalars().all())
    
    async def get_applicable_fee(
        self,
        db: AsyncSession,
        from_country_id: UUID,
        to_country_id: UUID,
        amount: Decimal
    ) -> Optional[Fee]:
        """
        Récupère le frais applicable pour un montant
        
        Args:
            db: Session asynchrone
            from_country_id: UUID du pays source
            to_country_id: UUID du pays destination
            amount: Montant du transfert
            
        Returns:
            Le frais applicable ou None
        """
        result = await db.execute(
            select(Fee)
            .where(
                Fee.from_country_id == from_country_id,
                Fee.to_country_id == to_country_id,
                Fee.is_active == True,
                Fee.min_amount <= amount,
                or_(Fee.max_amount == None, Fee.max_amount >= amount)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_type(self, db: AsyncSession, fee_type: FeeType) -> List[Fee]:
        """
        Récupère les frais par type
        
        Args:
            db: Session asynchrone
            fee_type: Type de frais
            
        Returns:
            Liste des frais
        """
        result = await db.execute(
            select(Fee).where(Fee.fee_type == fee_type)
        )
        return list(result.scalars().all())
    
    async def get_active_fees(self, db: AsyncSession) -> List[Fee]:
        """
        Récupère les frais actifs
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des frais actifs
        """
        result = await db.execute(
            select(Fee).where(Fee.is_active == True)
        )
        return list(result.scalars().all())
    
    async def activate(self, db: AsyncSession, fee_id: UUID) -> Optional[Fee]:
        """Active un frais"""
        fee = await self.get(db, fee_id)
        if fee:
            fee.is_active = True
            await db.flush()
            await db.refresh(fee)
        return fee
    
    async def deactivate(self, db: AsyncSession, fee_id: UUID) -> Optional[Fee]:
        """Désactive un frais"""
        fee = await self.get(db, fee_id)
        if fee:
            fee.is_active = False
            await db.flush()
            await db.refresh(fee)
        return fee


# Instance globale
fee_repository = FeeRepository()