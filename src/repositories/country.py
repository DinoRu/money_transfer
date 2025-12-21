"""
Repository pour le modèle Country en mode asynchrone
"""
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Country
from .base import BaseRepository


class CountryRepository(BaseRepository[Country]):
    """Repository pour gérer les pays"""
    
    def __init__(self):
        super().__init__(Country)
    
    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Country]:
        """
        Récupère un pays par son nom
        
        Args:
            db: Session asynchrone
            name: Nom du pays
            
        Returns:
            Le pays ou None
        """
        result = await db.execute(
            select(Country).where(Country.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Country]:
        """
        Récupère un pays par son code
        
        Args:
            db: Session asynchrone
            code: Code du pays (ex: FR, US)
            
        Returns:
            Le pays ou None
        """
        result = await db.execute(
            select(Country).where(Country.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_with_currency(self, db: AsyncSession, country_id: UUID) -> Optional[Country]:
        """
        Récupère un pays avec sa devise
        
        Args:
            db: Session asynchrone
            country_id: UUID du pays
            
        Returns:
            Le pays avec devise ou None
        """
        result = await db.execute(
            select(Country)
            .options(selectinload(Country.currency))
            .where(Country.id == country_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_with_currencies(self, db: AsyncSession) -> List[Country]:
        """
        Récupère tous les pays avec leurs devises
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des pays avec devises
        """
        result = await db.execute(
            select(Country).options(selectinload(Country.currency))
        )
        return list(result.scalars().all())
    
    async def get_sender_countries(self, db: AsyncSession) -> List[Country]:
        """
        Récupère les pays depuis lesquels on peut envoyer
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des pays expéditeurs
        """
        result = await db.execute(
            select(Country)
            .options(selectinload(Country.currency))
            .where(Country.can_send_from == True)
        )
        return list(result.scalars().all())
    
    async def get_receiver_countries(self, db: AsyncSession) -> List[Country]:
        """
        Récupère les pays vers lesquels on peut envoyer
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des pays destinataires
        """
        result = await db.execute(
            select(Country)
            .options(selectinload(Country.currency))
            .where(Country.can_send_to == True)
        )
        return list(result.scalars().all())
    
    async def get_by_currency(self, db: AsyncSession, currency_id: UUID) -> List[Country]:
        """
        Récupère les pays utilisant une devise spécifique
        
        Args:
            db: Session asynchrone
            currency_id: UUID de la devise
            
        Returns:
            Liste des pays
        """
        result = await db.execute(
            select(Country).where(Country.currency_id == currency_id)
        )
        return list(result.scalars().all())


# Instance globale du repository
country_repository = CountryRepository()