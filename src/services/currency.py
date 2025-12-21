"""
Exemple d'utilisation du BaseService amélioré avec Currency
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Currency
from src.repositories import currency_repository
from src.schemas.currency import CurrencyCreate, CurrencyUpdate, CurrencyResponse
from .base import BaseService


class CurrencyService(BaseService[Currency, CurrencyCreate, CurrencyUpdate, CurrencyResponse]):
    """
    Service pour les devises héritant du BaseService
    
    Hérite automatiquement de:
    - create()
    - get()
    - get_multi()
    - update()
    - delete()
    - exists()
    - count()
    - get_or_404()
    - create_bulk()
    - update_partial()
    - soft_delete()
    - restore()
    - get_active()
    - activate()
    - deactivate()
    - search()
    - get_by_field()
    - get_multi_by_field()
    """
    
    def __init__(self):
        super().__init__(currency_repository, CurrencyResponse)
    
    # ========================================
    # Méthodes spécifiques à Currency
    # ========================================
    
    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[CurrencyResponse]:
        """
        Récupère une devise par code ISO
        
        Note: Utilise get_by_field() du BaseService
        """
        return await self.get_by_field(db, "code", code)
    
    async def get_active_currencies(self, db: AsyncSession) -> List[CurrencyResponse]:
        """
        Récupère les devises actives
        
        Note: Utilise get_active() du BaseService
        """
        return await self.get_active(db)
    
    async def search_by_name(
        self,
        db: AsyncSession,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[CurrencyResponse]:
        """
        Recherche des devises par nom
        
        Note: Utilise search() du BaseService
        """
        return await self.search(db, "name", search_term, skip, limit)
    
    async def create_with_validation(
        self,
        db: AsyncSession,
        obj_in: CurrencyCreate
    ) -> CurrencyResponse:
        """
        Crée une devise avec validation métier supplémentaire
        
        Args:
            db: Session asynchrone
            obj_in: Données de la devise
            
        Returns:
            La devise créée
            
        Raises:
            ValueError: Si le code existe déjà ou validation échoue
        """
        # Validation: code unique
        existing = await self.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Le code de devise {obj_in.code} existe déjà")
        
        # Validation: code en majuscules
        if obj_in.code != obj_in.code.upper():
            raise ValueError("Le code de devise doit être en majuscules")
        
        # Validation: longueur du code (ISO 4217)
        if len(obj_in.code) != 3:
            raise ValueError("Le code de devise doit contenir 3 caractères")
        
        # Créer avec le BaseService
        return await self.create(db, obj_in)
    
    async def get_statistics(self, db: AsyncSession) -> dict:
        """
        Récupère les statistiques des devises
        
        Returns:
            Dictionnaire avec les statistiques
        """
        total = await self.count(db)
        active = len(await self.get_active(db, limit=1000))
        
        return {
            "total_currencies": total,
            "active_currencies": active,
            "inactive_currencies": total - active
        }
    
    async def bulk_activate(
        self,
        db: AsyncSession,
        currency_ids: List[UUID]
    ) -> List[CurrencyResponse]:
        """
        Active plusieurs devises en une fois
        
        Args:
            db: Session asynchrone
            currency_ids: Liste des UUIDs des devises
            
        Returns:
            Liste des devises activées
        """
        activated = []
        for currency_id in currency_ids:
            currency = await self.activate(db, currency_id)
            if currency:
                activated.append(currency)
        
        await db.flush()
        return activated
    
    async def bulk_deactivate(
        self,
        db: AsyncSession,
        currency_ids: List[UUID]
    ) -> List[CurrencyResponse]:
        """
        Désactive plusieurs devises en une fois
        
        Args:
            db: Session asynchrone
            currency_ids: Liste des UUIDs des devises
            
        Returns:
            Liste des devises désactivées
        """
        deactivated = []
        for currency_id in currency_ids:
            currency = await self.deactivate(db, currency_id)
            if currency:
                deactivated.append(currency)
        
        await db.flush()
        return deactivated


# Instance globale du service
currency_service = CurrencyService()

