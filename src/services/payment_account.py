"""
Service pour les comptes de paiement en mode asynchrone
"""
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import PaymentAccount
from src.repositories import payment_account_repository, payment_partner_repository
from src.schemas.payment_account import PaymentAccountCreate, PaymentAccountUpdate, PaymentAccountResponse, PaymentAccountWithPartner
from .base import BaseService


class PaymentAccountService(BaseService[PaymentAccount, PaymentAccountCreate, PaymentAccountUpdate, PaymentAccountResponse]):
    """Service pour la gestion des comptes de paiement"""
    
    def __init__(self):
        super().__init__(payment_account_repository, PaymentAccountResponse)
    
    async def get_with_partner(self, db: AsyncSession, account_id: UUID) -> Optional[PaymentAccountWithPartner]:
        """Récupère un compte avec partenaire"""
        account = await self.repository.get_with_partner(db, account_id)
        if account:
            return PaymentAccountWithPartner.model_validate(account)
        return None
    
    async def get_by_partner(self, db: AsyncSession, partner_id: UUID) -> List[PaymentAccountResponse]:
        """Récupère les comptes d'un partenaire"""
        accounts = await self.repository.get_by_partner(db, partner_id)
        return [PaymentAccountResponse.model_validate(a) for a in accounts]
    
    async def get_active_by_partner(self, db: AsyncSession, partner_id: UUID) -> List[PaymentAccountResponse]:
        """Récupère les comptes actifs d'un partenaire"""
        accounts = await self.repository.get_active_by_partner(db, partner_id)
        return [PaymentAccountResponse.model_validate(a) for a in accounts]
    
    async def get_by_account_number(self, db: AsyncSession, account_number: str) -> Optional[PaymentAccountWithPartner]:
        """Récupère un compte par numéro"""
        account = await self.repository.get_by_account_number(db, account_number)
        if account:
            return PaymentAccountWithPartner.model_validate(account)
        return None
    
    async def validate_account_for_transaction(self, db: AsyncSession, account_id: UUID) -> Tuple[bool, Optional[str]]:
        """Valide qu'un compte peut être utilisé pour une transaction"""
        account = await self.repository.get_with_partner(db, account_id)
        
        if not account:
            return False, "Compte non trouvé"
        
        if not account.is_active:
            return False, "Compte inactif"
        
        if not account.payment_partner.is_active:
            return False, "Partenaire de paiement inactif"
        
        return True, None
    
    async def get_statistics(self, db: AsyncSession, partner_id: UUID) -> dict:
        """Récupère les statistiques des comptes d'un partenaire"""
        all_accounts = await self.repository.get_by_partner(db, partner_id)
        active_accounts = [a for a in all_accounts if a.is_active]
        
        return {
            "total_accounts": len(all_accounts),
            "active_accounts": len(active_accounts),
            "inactive_accounts": len(all_accounts) - len(active_accounts),
            "accounts_with_number": len([a for a in all_accounts if a.account_number]),
            "accounts_with_bank": len([a for a in all_accounts if a.bank_name])
        }
    
    async def create(self, db: AsyncSession, obj_in: PaymentAccountCreate) -> PaymentAccountResponse:
        """Crée un compte avec validation"""
        # Vérifier que le partenaire existe et est actif
        partner = await payment_partner_repository.get(db, obj_in.payment_partner_id)
        if not partner:
            raise ValueError("Partenaire de paiement non trouvé")
        
        if not partner.is_active:
            raise ValueError("Partenaire de paiement inactif")
        
        # Vérifier l'unicité du numéro de compte
        if obj_in.account_number:
            if await self.repository.account_number_exists(db, obj_in.account_number):
                raise ValueError(f"Le numéro de compte {obj_in.account_number} existe déjà")
        
        return await super().create(db, obj_in)


# Instance globale
payment_account_service = PaymentAccountService()