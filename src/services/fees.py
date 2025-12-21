"""
Service pour les frais en mode asynchrone
"""
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Fee
from src.models.enums import FeeType
from src.repositories import fee_repository
from src.schemas.fees import FeeCreate, FeeUpdate, FeeResponse, FeeWithCountries, FeeCalculation, FeeCalculationResponse
from .base import BaseService


class FeeService(BaseService[Fee, FeeCreate, FeeUpdate, FeeResponse]):
    """Service pour la gestion des frais"""
    
    def __init__(self):
        super().__init__(fee_repository, FeeResponse)
    
    async def get_with_countries(self, db: AsyncSession, fee_id: UUID) -> Optional[FeeWithCountries]:
        """Récupère un frais avec pays"""
        fee = await self.repository.get_with_countries(db, fee_id)
        if fee:
            return FeeWithCountries.model_validate(fee)
        return None
    
    async def get_all_with_countries(self, db: AsyncSession) -> List[FeeWithCountries]:
        """Récupère tous les frais avec pays"""
        fees = await self.repository.get_all_with_countries(db)
        return [FeeWithCountries.model_validate(f) for f in fees]
    
    async def get_by_corridor(
        self,
        db: AsyncSession,
        from_country_id: UUID,
        to_country_id: UUID
    ) -> List[FeeWithCountries]:
        """Récupère les frais d'un corridor"""
        fees = await self.repository.get_by_corridor(db, from_country_id, to_country_id)
        return [FeeWithCountries.model_validate(f) for f in fees]
    
    async def calculate_fee(
        self,
        db: AsyncSession,
        calculation: FeeCalculation
    ) -> FeeCalculationResponse:
        """Calcule les frais pour un transfert"""
        fee = await self.repository.get_applicable_fee(
            db,
            calculation.from_country_id,
            calculation.to_country_id,
            calculation.amount
        )
        
        if not fee:
            raise ValueError("Pas de frais configurés pour ce corridor et ce montant")
        
        fee_full = await self.repository.get_with_countries(db, fee.id)
        
        calculated_fee = self._calculate_fee_amount(fee, calculation.amount)
        
        return FeeCalculationResponse(
            from_country=fee_full.from_country,
            to_country=fee_full.to_country,
            amount=calculation.amount,
            fee_type=fee.fee_type,
            fee_value=fee.fee_value,
            calculated_fee=calculated_fee,
            total_amount=calculation.amount + calculated_fee
        )
    
    def _calculate_fee_amount(self, fee: Fee, amount: Decimal) -> Decimal:
        """Calcule le montant des frais"""
        if fee.fee_type == FeeType.PERCENTAGE:
            return (amount * fee.fee_value) / Decimal("100")
        elif fee.fee_type == FeeType.FIXED:
            return fee.fee_value
        elif fee.fee_type == FeeType.TIERED:
            return fee.fee_value
        return Decimal("0")


# Instance globale
fee_service = FeeService()