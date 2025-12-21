"""
Repository pour le modèle PaymentPartner en mode asynchrone
"""
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import PaymentPartner
from src.models.enums import PaymentPartnerType
from .base import BaseRepository


class PaymentPartnerRepository(BaseRepository[PaymentPartner]):
    """Repository pour gérer les partenaires de paiement"""
    
    def __init__(self):
        super().__init__(PaymentPartner)
    
    async def get_with_country(
        self,
        db: AsyncSession,
        partner_id: UUID
    ) -> Optional[PaymentPartner]:
        """
        Récupère un partenaire avec son pays
        
        Args:
            db: Session asynchrone
            partner_id: UUID du partenaire
            
        Returns:
            Le partenaire avec pays ou None
        """
        result = await db.execute(
            select(PaymentPartner)
            .options(selectinload(PaymentPartner.country))
            .where(PaymentPartner.id == partner_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_country(
        self,
        db: AsyncSession,
        country_id: UUID
    ) -> List[PaymentPartner]:
        """
        Récupère les partenaires d'un pays
        
        Args:
            db: Session asynchrone
            country_id: UUID du pays
            
        Returns:
            Liste des partenaires
        """
        result = await db.execute(
            select(PaymentPartner)
            .options(selectinload(PaymentPartner.country))
            .where(PaymentPartner.country_id == country_id)
        )
        return list(result.scalars().all())
    
    async def get_by_type(
        self,
        db: AsyncSession,
        partner_type: PaymentPartnerType
    ) -> List[PaymentPartner]:
        """
        Récupère les partenaires par type
        
        Args:
            db: Session asynchrone
            partner_type: Type de partenaire
            
        Returns:
            Liste des partenaires
        """
        result = await db.execute(
            select(PaymentPartner).where(PaymentPartner.type == partner_type)
        )
        return list(result.scalars().all())
    
    async def get_active_partners(self, db: AsyncSession) -> List[PaymentPartner]:
        """
        Récupère les partenaires actifs
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des partenaires actifs
        """
        result = await db.execute(
            select(PaymentPartner)
            .options(selectinload(PaymentPartner.country))
            .where(PaymentPartner.is_active == True)
        )
        return list(result.scalars().all())
    
    async def get_send_partners(
        self,
        db: AsyncSession,
        country_id: Optional[UUID] = None
    ) -> List[PaymentPartner]:
        """
        Récupère les partenaires pouvant envoyer
        
        Args:
            db: Session asynchrone
            country_id: Optionnel - filtre par pays
            
        Returns:
            Liste des partenaires
        """
        query = select(PaymentPartner).options(
            selectinload(PaymentPartner.country)
        ).where(
            PaymentPartner.can_send == True,
            PaymentPartner.is_active == True
        )
        
        if country_id:
            query = query.where(PaymentPartner.country_id == country_id)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_receive_partners(
        self,
        db: AsyncSession,
        country_id: Optional[UUID] = None
    ) -> List[PaymentPartner]:
        """
        Récupère les partenaires pouvant recevoir
        
        Args:
            db: Session asynchrone
            country_id: Optionnel - filtre par pays
            
        Returns:
            Liste des partenaires
        """
        query = select(PaymentPartner).options(
            selectinload(PaymentPartner.country)
        ).where(
            PaymentPartner.can_receive == True,
            PaymentPartner.is_active == True
        )
        
        if country_id:
            query = query.where(PaymentPartner.country_id == country_id)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def activate(self, db: AsyncSession, partner_id: UUID) -> Optional[PaymentPartner]:
        """Active un partenaire"""
        partner = await self.get(db, partner_id)
        if partner:
            partner.is_active = True
            await db.flush()
            await db.refresh(partner)
        return partner
    
    async def deactivate(self, db: AsyncSession, partner_id: UUID) -> Optional[PaymentPartner]:
        """Désactive un partenaire"""
        partner = await self.get(db, partner_id)
        if partner:
            partner.is_active = False
            await db.flush()
            await db.refresh(partner)
        return partner


# Instance globale
payment_partner_repository = PaymentPartnerRepository()