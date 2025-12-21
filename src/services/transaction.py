"""
Service pour la gestion des transactions
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.models import Transfer
from src.models.enums import TransactionStatus
from src.repositories import transaction_repository, user_repository
from src.schemas.transfer import (
    TransferCreate, TransferUpdate, TransferResponse,
    TransferWithSender, TransferFilter
)
from src.models.transfer import Transfer
from .base import BaseService


class TransactionService(BaseService[Transfer, TransferCreate, TransferUpdate, TransferResponse]):
    """Service pour la gestion des transactions"""
    
    def __init__(self):
        super().__init__(transaction_repository, TransferResponse)
        self.repository = transaction_repository
        self.user_repository = user_repository
    
    def create(self, db: Session, obj_in: TransferCreate) -> TransferResponse:
        """
        Crée une nouvelle transaction avec validation
        
        Args:
            db: Session de base de données
            obj_in: Données de la transaction
            
        Returns:
            La transaction créée
            
        Raises:
            ValueError: Si la validation échoue
        """
        # Vérifier que l'expéditeur existe
        sender = self.user_repository.get(db, obj_in.sender_id)
        if not sender:
            raise ValueError("Expéditeur non trouvé")
        
        # Validation des montants
        if obj_in.sender_amount <= 0:
            raise ValueError("Le montant d'envoi doit être positif")
        
        if obj_in.receiver_amount <= 0:
            raise ValueError("Le montant de réception doit être positif")
        
        if obj_in.exchange_rate <= 0:
            raise ValueError("Le taux de change doit être positif")
        
        if obj_in.total_to_pay < obj_in.sender_amount:
            raise ValueError("Le montant total doit être supérieur ou égal au montant d'envoi")
        
        # Créer la transaction
        transaction = self.repository.create(db, obj_in=obj_in)
        return TransferResponse.model_validate(transaction)
    
    def get_with_sender(self, db: Session, id: UUID) -> Optional[TransferWithSender]:
        """
        Récupère une transaction avec les détails de l'expéditeur
        
        Args:
            db: Session de base de données
            id: UUID de la transaction
            
        Returns:
            La transaction avec expéditeur ou None
        """
        transaction = self.repository.get_with_sender(db, id)
        if transaction:
            return TransferWithSender.model_validate(transaction)
        return None
    
    def get_by_reference(self, db: Session, reference: str) -> Optional[TransferResponse]:
        """
        Récupère une transaction par sa référence
        
        Args:
            db: Session de base de données
            reference: Référence de la transaction
            
        Returns:
            La transaction ou None
        """
        transaction = self.repository.get_by_reference(db, reference)
        if transaction:
            return TransferResponse.model_validate(transaction)
        return None
    
    def get_by_sender(
        self,
        db: Session,
        sender_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[TransferResponse]:
        """
        Récupère les transactions d'un expéditeur
        
        Args:
            db: Session de base de données
            sender_id: UUID de l'expéditeur
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des transactions
        """
        transactions = self.repository.get_by_sender(db, sender_id, skip=skip, limit=limit)
        return [TransferResponse.model_validate(txn) for txn in transactions]
    
    def get_by_status(
        self,
        db: Session,
        status: TransactionStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[TransferResponse]:
        """
        Récupère les transactions par statut
        
        Args:
            db: Session de base de données
            status: Statut des transactions
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des transactions
        """
        transactions = self.repository.get_by_status(db, status, skip=skip, limit=limit)
        return [TransferResponse.model_validate(txn) for txn in transactions]
    
    def search_transactions(
        self,
        db: Session,
        filters: TransferFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[TransferResponse]:
        """
        Recherche avancée de transactions
        
        Args:
            db: Session de base de données
            filters: Filtres de recherche
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des transactions correspondantes
        """
        transactions = self.repository.search_transactions(
            db,
            sender_id=filters.sender_id,
            status=filters.status,
            sender_country=filters.sender_country,
            receiver_country=filters.receiver_country,
            min_amount=filters.min_amount,
            max_amount=filters.max_amount,
            start_date=filters.start_date,
            end_date=filters.end_date,
            skip=skip,
            limit=limit
        )
        return [TransferResponse.model_validate(txn) for txn in transactions]
    
    def update_status(
        self,
        db: Session,
        transaction_id: UUID,
        new_status: TransactionStatus,
        notes: Optional[str] = None
    ) -> Optional[TransferResponse]:
        """
        Met à jour le statut d'une transaction avec validation
        
        Args:
            db: Session de base de données
            transaction_id: UUID de la transaction
            new_status: Nouveau statut
            notes: Notes additionnelles
            
        Returns:
            La transaction mise à jour ou None
            
        Raises:
            ValueError: Si la transition de statut est invalide
        """
        transaction = self.repository.get(db, transaction_id)
        if not transaction:
            return None
        
        # Validation de la transition de statut
        current_status = TransactionStatus(transaction.status)
        if not self._is_valid_status_transition(current_status, new_status):
            raise ValueError(
                f"Transition de statut invalide: {current_status.value} -> {new_status.value}"
            )
        
        # Mise à jour du statut
        updated_transaction = self.repository.update_status(
            db,
            transaction_id,
            new_status,
            notes
        )
        
        if updated_transaction:
            return TransferResponse.model_validate(updated_transaction)
        return None
    
    def cancel_transaction(
        self,
        db: Session,
        transaction_id: UUID,
        reason: Optional[str] = None
    ) -> Optional[TransferResponse]:
        """
        Annule une transaction
        
        Args:
            db: Session de base de données
            transaction_id: UUID de la transaction
            reason: Raison de l'annulation
            
        Returns:
            La transaction annulée ou None
        """
        return self.update_status(
            db,
            transaction_id,
            TransactionStatus.CANCELLED,
            reason
        )
    
    def complete_transaction(
        self,
        db: Session,
        transaction_id: UUID
    ) -> Optional[TransferResponse]:
        """
        Marque une transaction comme complétée
        
        Args:
            db: Session de base de données
            transaction_id: UUID de la transaction
            
        Returns:
            La transaction complétée ou None
        """
        return self.update_status(
            db,
            transaction_id,
            TransactionStatus.COMPLETED
        )
    
    def get_user_statistics(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """
        Récupère les statistiques d'un utilisateur
        
        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur
            
        Returns:
            Dictionnaire avec les statistiques
            
        Raises:
            ValueError: Si l'utilisateur n'existe pas
        """
        user = self.user_repository.get(db, user_id)
        if not user:
            raise ValueError("Utilisateur non trouvé")
        
        return self.repository.get_user_statistics(db, user_id)
    
    def get_pending_transactions(self, db: Session) -> List[TransferResponse]:
        """
        Récupère toutes les transactions en attente
        
        Args:
            db: Session de base de données
            
        Returns:
            Liste des transactions en attente
        """
        transactions = self.repository.get_pending_transactions(db)
        return [TransferResponse.model_validate(txn) for txn in transactions]
    
    def _is_valid_status_transition(
        self,
        current_status: TransactionStatus,
        new_status: TransactionStatus
    ) -> bool:
        """
        Valide une transition de statut
        
        Args:
            current_status: Statut actuel
            new_status: Nouveau statut
            
        Returns:
            True si la transition est valide
        """
        # Définir les transitions valides
        valid_transitions = {
            TransactionStatus.AWAITING_PAYMENT: [
                TransactionStatus.FOUNDS_DEPOSITED,
                TransactionStatus.CANCELLED,
                TransactionStatus.EXPIRED
            ],
            TransactionStatus.FOUNDS_DEPOSITED: [
                TransactionStatus.COMPLETED,
                TransactionStatus.CANCELLED
            ],
            TransactionStatus.COMPLETED: [],  # État final
            TransactionStatus.CANCELLED: [],  # État final
            TransactionStatus.EXPIRED: []     # État final
        }
        
        return new_status in valid_transitions.get(current_status, [])


# Instance globale du service
transaction_service = TransactionService()