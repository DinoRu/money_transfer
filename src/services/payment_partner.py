"""
Service pour les partenaires de paiement en mode asynchrone
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import PaymentPartner
from src.models.enums import PaymentPartnerType
from src.repositories import payment_partner_repository
from src.schemas.payment_partner import PaymentPartnerCreate, PaymentPartnerUpdate, PaymentPartnerResponse, PaymentPartnerWithCountry
from .base import BaseService


class PaymentPartnerService(BaseService[PaymentPartner, PaymentPartnerCreate, PaymentPartnerUpdate, PaymentPartnerResponse]):
    """Service pour la gestion des partenaires de paiement"""
    
    def __init__(self):
        super().__init__(payment_partner_repository, PaymentPartnerResponse)
    
    async def get_with_country(self, db: AsyncSession, partner_id: UUID) -> Optional[PaymentPartnerWithCountry]:
        """Récupère un partenaire avec pays"""
        partner = await self.repository.get_with_country(db, partner_id)
        if partner:
            return PaymentPartnerWithCountry.model_validate(partner)
        return None
    
    async def get_by_country(self, db: AsyncSession, country_id: UUID) -> List[PaymentPartnerResponse]:
        """Récupère les partenaires d'un pays"""
        partners = await self.repository.get_by_country(db, country_id)
        return [PaymentPartnerResponse.model_validate(p) for p in partners]
    
    async def get_by_type(self, db: AsyncSession, partner_type: PaymentPartnerType) -> List[PaymentPartnerResponse]:
        """Récupère les partenaires par type"""
        partners = await self.repository.get_by_type(db, partner_type)
        return [PaymentPartnerResponse.model_validate(p) for p in partners]
    
    async def get_send_partners(
        self,
        db: AsyncSession,
        country_id: Optional[UUID] = None
    ) -> List[PaymentPartnerWithCountry]:
        """Récupère les partenaires pouvant envoyer"""
        partners = await self.repository.get_send_partners(db, country_id)
        return [PaymentPartnerWithCountry.model_validate(p) for p in partners]
    
    async def get_receive_partners(
        self,
        db: AsyncSession,
        country_id: Optional[UUID] = None
    ) -> List[PaymentPartnerWithCountry]:
        """Récupère les partenaires pouvant recevoir"""
        partners = await self.repository.get_receive_partners(db, country_id)
        return [PaymentPartnerWithCountry.model_validate(p) for p in partners]
    
    async def get_available_for_corridor(
        self,
        db: AsyncSession,
        sender_country_id: UUID,
        receiver_country_id: UUID
    ) -> dict:
        """Récupère les partenaires disponibles pour un corridor"""
        send_partners = await self.get_send_partners(db, sender_country_id)
        receive_partners = await self.get_receive_partners(db, receiver_country_id)
        
        return {
            "send_partners": send_partners,
            "receive_partners": receive_partners,
            "total_send": len(send_partners),
            "total_receive": len(receive_partners)
        }


# Instance globale
payment_partner_service = PaymentPartnerService()
