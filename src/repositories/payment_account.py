"""
Repository pour le modèle PaymentAccount en mode asynchrone
"""
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import PaymentAccount
from .base import BaseRepository


class PaymentAccountRepository(BaseRepository[PaymentAccount]):
    """Repository pour gérer les comptes de paiement"""
    
    def __init__(self):
        super().__init__(PaymentAccount)
    
    async def get_with_partner(
        self,
        db: AsyncSession,
        account_id: UUID
    ) -> Optional[PaymentAccount]:
        """
        Récupère un compte avec son partenaire
        
        Args:
            db: Session asynchrone
            account_id: UUID du compte
            
        Returns:
            Le compte avec partenaire ou None
        """
        result = await db.execute(
            select(PaymentAccount)
            .options(selectinload(PaymentAccount.payment_partner))
            .where(PaymentAccount.id == account_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_partner(
        self,
        db: AsyncSession,
        partner_id: UUID
    ) -> List[PaymentAccount]:
        """
        Récupère les comptes d'un partenaire
        
        Args:
            db: Session asynchrone
            partner_id: UUID du partenaire
            
        Returns:
            Liste des comptes
        """
        result = await db.execute(
            select(PaymentAccount)
            .options(selectinload(PaymentAccount.payment_partner))
            .where(PaymentAccount.payment_partner_id == partner_id)
        )
        return list(result.scalars().all())
    
    async def get_active_by_partner(
        self,
        db: AsyncSession,
        partner_id: UUID
    ) -> List[PaymentAccount]:
        """
        Récupère les comptes actifs d'un partenaire
        
        Args:
            db: Session asynchrone
            partner_id: UUID du partenaire
            
        Returns:
            Liste des comptes actifs
        """
        result = await db.execute(
            select(PaymentAccount)
            .options(selectinload(PaymentAccount.payment_partner))
            .where(
                PaymentAccount.payment_partner_id == partner_id,
                PaymentAccount.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def get_by_account_number(
        self,
        db: AsyncSession,
        account_number: str
    ) -> Optional[PaymentAccount]:
        """
        Récupère un compte par numéro
        
        Args:
            db: Session asynchrone
            account_number: Numéro du compte
            
        Returns:
            Le compte ou None
        """
        result = await db.execute(
            select(PaymentAccount)
            .options(selectinload(PaymentAccount.payment_partner))
            .where(PaymentAccount.account_number == account_number)
        )
        return result.scalar_one_or_none()
    
    async def get_active_accounts(self, db: AsyncSession) -> List[PaymentAccount]:
        """
        Récupère tous les comptes actifs
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des comptes actifs
        """
        result = await db.execute(
            select(PaymentAccount)
            .options(selectinload(PaymentAccount.payment_partner))
            .where(PaymentAccount.is_active == True)
        )
        return list(result.scalars().all())
    
    async def account_number_exists(
        self,
        db: AsyncSession,
        account_number: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Vérifie si un numéro de compte existe
        
        Args:
            db: Session asynchrone
            account_number: Numéro à vérifier
            exclude_id: ID à exclure de la vérification
            
        Returns:
            True si le numéro existe
        """
        query = select(PaymentAccount).where(
            PaymentAccount.account_number == account_number
        )
        
        if exclude_id:
            query = query.where(PaymentAccount.id != exclude_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def activate(self, db: AsyncSession, account_id: UUID) -> Optional[PaymentAccount]:
        """Active un compte"""
        account = await self.get(db, account_id)
        if account:
            account.is_active = True
            await db.flush()
            await db.refresh(account)
        return account
    
    async def deactivate(self, db: AsyncSession, account_id: UUID) -> Optional[PaymentAccount]:
        """Désactive un compte"""
        account = await self.get(db, account_id)
        if account:
            account.is_active = False
            await db.flush()
            await db.refresh(account)
        return account


# Instance globale
payment_account_repository = PaymentAccountRepository()