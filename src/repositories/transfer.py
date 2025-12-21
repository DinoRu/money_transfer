"""
Repository pour le modèle Transfer
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import Session, joinedload, selectinload

from src.models import Transfer
from src.models.enums import TransactionStatus
from src.schemas.transfer import TransferCreate, TransferUpdate
from src.models.transfer import Transfer
from .base import BaseRepository


class TransactionRepository(BaseRepository[Transfer]):
    """Repository pour gérer les transactions"""
    
    def __init__(self):
        super().__init__(Transfer)
    
    def get_with_sender(self, db: Session, id: UUID) -> Optional[Transfer]:
        """
        Récupère une transaction avec l'expéditeur
        
        Args:
            db: Session de base de données
            id: UUID de la transaction
            
        Returns:
            La transaction avec l'expéditeur
        """
        return db.query(Transfer).options(
            selectinload(Transfer.sender)
        ).filter(Transfer.id == id).first()
    
    def get_by_reference(self, db: Session, reference: str) -> Optional[Transfer]:
        """
        Récupère une transaction par sa référence
        
        Args:
            db: Session de base de données
            reference: Référence de la transaction
            
        Returns:
            La transaction ou None
        """
        return db.query(Transfer).filter(
            Transfer.reference == reference
        ).first()
    
    def get_by_sender(
        self,
        db: Session,
        sender_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transfer]:
        """
        Récupère les transactions d'un expéditeur
        
        Args:
            db: Session de base de données
            sender_id: ID de l'expéditeur
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des transactions
        """
        return db.query(Transfer).filter(
            Transfer.sender_id == sender_id
        ).order_by(desc(Transfer.created_at)).offset(skip).limit(limit).all()
    
    def get_by_status(
        self,
        db: Session,
        status: TransactionStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transfer]:
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
        return db.query(Transfer).filter(
            Transfer.status == status.value
        ).order_by(desc(Transfer.created_at)).offset(skip).limit(limit).all()
    
    def get_pending_transactions(self, db: Session) -> List[Transfer]:
        """
        Récupère toutes les transactions en attente
        
        Args:
            db: Session de base de données
            
        Returns:
            Liste des transactions en attente
        """
        return db.query(Transfer).filter(
            Transfer.status == TransactionStatus.AWAITING_PAYMENT.value
        ).all()
    
    def get_by_date_range(
        self,
        db: Session,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transfer]:
        """
        Récupère les transactions dans une période
        
        Args:
            db: Session de base de données
            start_date: Date de début
            end_date: Date de fin
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des transactions
        """
        return db.query(Transfer).filter(
            and_(
                Transfer.created_at >= start_date,
                Transfer.created_at <= end_date
            )
        ).order_by(desc(Transfer.created_at)).offset(skip).limit(limit).all()
    
    def get_by_corridor(
        self,
        db: Session,
        sender_country: str,
        receiver_country: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transfer]:
        """
        Récupère les transactions par corridor
        
        Args:
            db: Session de base de données
            sender_country: Pays d'envoi
            receiver_country: Pays de réception
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des transactions
        """
        return db.query(Transfer).filter(
            and_(
                Transfer.sender_country == sender_country,
                Transfer.receiver_country == receiver_country
            )
        ).order_by(desc(Transfer.created_at)).offset(skip).limit(limit).all()
    
    def search_transactions(
        self,
        db: Session,
        *,
        sender_id: Optional[UUID] = None,
        status: Optional[TransactionStatus] = None,
        sender_country: Optional[str] = None,
        receiver_country: Optional[str] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transfer]:
        """
        Recherche avancée de transactions avec plusieurs filtres
        
        Args:
            db: Session de base de données
            sender_id: ID de l'expéditeur
            status: Statut de la transaction
            sender_country: Pays d'envoi
            receiver_country: Pays de réception
            min_amount: Montant minimum
            max_amount: Montant maximum
            start_date: Date de début
            end_date: Date de fin
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des transactions correspondantes
        """
        query = db.query(Transfer)
        
        filters = []
        
        if sender_id:
            filters.append(Transfer.sender_id == sender_id)
        
        if status:
            filters.append(Transfer.status == status.value)
        
        if sender_country:
            filters.append(Transfer.sender_country == sender_country)
        
        if receiver_country:
            filters.append(Transfer.receiver_country == receiver_country)
        
        if min_amount:
            filters.append(Transfer.sender_amount >= min_amount)
        
        if max_amount:
            filters.append(Transfer.sender_amount <= max_amount)
        
        if start_date:
            filters.append(Transfer.created_at >= start_date)
        
        if end_date:
            filters.append(Transfer.created_at <= end_date)
        
        if filters:
            query = query.filter(and_(*filters))
        
        return query.order_by(desc(Transfer.created_at)).offset(skip).limit(limit).all()
    
    def update_status(
        self,
        db: Session,
        transfer_id: UUID,
        new_status: TransactionStatus,
        notes: Optional[str] = None
    ) -> Optional[Transfer]:
        """
        Met à jour le statut d'une transaction
        
        Args:
            db: Session de base de données
            transaction_id: ID de la transaction
            new_status: Nouveau statut
            notes: Notes additionnelles
            
        Returns:
            La transaction mise à jour
        """
        transfer = self.get(db, transfer_id)
        if not transfer:
            return None
        
        transfer.status = new_status.value
        if notes:
            transfer.notes = notes
        
        # Mise à jour des timestamps selon le statut
        now = datetime.now()
        if new_status == TransactionStatus.COMPLETED:
            transfer.completed_at = now
        elif new_status == TransactionStatus.FOUNDS_DEPOSITED:
            transfer.paid_at = now
        elif new_status == TransactionStatus.CANCELLED:
            transfer.cancelled_at = now
        elif new_status == TransactionStatus.EXPIRED:
            transfer.expired_at = now
        
        db.commit()
        db.refresh(transfer)
        return transfer
    
    def get_user_statistics(self, db: Session, user_id: UUID) -> dict:
        """
        Calcule les statistiques de transaction d'un utilisateur
        
        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            
        Returns:
            Dictionnaire avec les statistiques
        """
        from sqlalchemy import func
        
        transactions = db.query(Transfer).filter(Transfer.sender_id == user_id)
        
        total = transactions.count()
        completed = transactions.filter(
            Transfer.status == TransactionStatus.COMPLETED.value
        ).count()
        pending = transactions.filter(
            Transfer.status == TransactionStatus.AWAITING_PAYMENT.value
        ).count()
        
        total_sent = db.query(
            func.sum(Transfer.sender_amount)
        ).filter(
            Transfer.sender_id == user_id,
            Transfer.status == TransactionStatus.COMPLETED.value
        ).scalar() or Decimal("0")
        
        return {
            "total_transactions": total,
            "completed_transactions": completed,
            "pending_transactions": pending,
            "total_amount_sent": float(total_sent)
        }


# Instance globale du repository
transaction_repository = TransactionRepository()