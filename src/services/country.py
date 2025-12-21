"""
Service pour les pays en mode asynchrone
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Country
from src.repositories import country_repository
from src.repositories import currency_repository
from src.schemas.country import CountryCreate, CountryUpdate, CountryResponse, CountryWithCurrency
from .base import BaseService


class CountryService(BaseService[Country, CountryCreate, CountryUpdate, CountryResponse]):
    """Service pour la gestion des pays"""
    
    def __init__(self):
        super().__init__(country_repository, CountryResponse)
    
    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[CountryResponse]:
        """Récupère un pays par nom"""
        country = await self.repository.get_by_name(db, name)
        if country:
            return CountryResponse.model_validate(country)
        return None
    
    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[CountryResponse]:
        """Récupère un pays par code"""
        country = await self.repository.get_by_code(db, code)
        if country:
            return CountryResponse.model_validate(country)
        return None
    
    async def get_with_currency(self, db: AsyncSession, country_id: UUID) -> Optional[CountryWithCurrency]:
        """Récupère un pays avec sa devise"""
        country = await self.repository.get_with_currency(db, country_id)
        if country:
            return CountryWithCurrency.model_validate(country)
        return None
    
    async def get_all_with_currencies(self, db: AsyncSession) -> List[CountryWithCurrency]:
        """Récupère tous les pays avec devises"""
        countries = await self.repository.get_all_with_currencies(db)
        return [CountryWithCurrency.model_validate(c) for c in countries]
    
    async def get_sender_countries(self, db: AsyncSession) -> List[CountryWithCurrency]:
        """Récupère les pays expéditeurs"""
        countries = await self.repository.get_sender_countries(db)
        return [CountryWithCurrency.model_validate(c) for c in countries]
    
    async def get_receiver_countries(self, db: AsyncSession) -> List[CountryWithCurrency]:
        """Récupère les pays destinataires"""
        countries = await self.repository.get_receiver_countries(db)
        return [CountryWithCurrency.model_validate(c) for c in countries]
    
    async def create(self, db: AsyncSession, obj_in: CountryCreate) -> CountryResponse:
        """Crée un pays avec validation"""
        # Vérifier que la devise existe
       
        currency = await currency_repository.get(db, obj_in.currency_id)
        if not currency:
            raise ValueError(f"La devise {obj_in.currency_id} n'existe pas")
        
        return await super().create(db, obj_in)


# Instance globale
country_service = CountryService()