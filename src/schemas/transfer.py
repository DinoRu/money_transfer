"""
Schemas pour le modèle Transaction
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field, EmailStr, field_validator

from src.models.enums import TransactionStatus
from .base import BaseSchema, IDMixin, TimestampMixin
from src.schemas.user import UserResponse


class TransferCreate(BaseSchema):
    """Schema pour créer une transaction"""
    sender_country: str = Field(..., max_length=200, description="Pays d'envoi")
    receiver_country: str = Field(..., max_length=200, description="Pays de réception")
    sender_partner: str = Field(..., max_length=20, description="Partenaire d'envoi")
    receiver_partner: str = Field(..., max_length=200, description="Partenaire de réception")
    
    sender_id: UUID = Field(..., description="ID de l'expéditeur")
    receiver_full_name: str = Field(..., min_length=2, max_length=100, description="Nom complet du bénéficiaire")
    receiver_phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$', description="Téléphone du bénéficiaire")
    receiver_email: Optional[EmailStr] = Field(None, description="Email du bénéficiaire")
    
    sender_amount: Decimal = Field(..., gt=0, description="Montant à envoyer")
    sender_currency: str = Field(..., min_length=3, max_length=3, description="Devise d'envoi")
    receiver_amount: Decimal = Field(..., gt=0, description="Montant à recevoir")
    receiver_currency: str = Field(..., min_length=3, max_length=3, description="Devise de réception")
    exchange_rate: Decimal = Field(..., gt=0, description="Taux de change appliqué")
    
    applied_fee: Decimal = Field(default=Decimal("0"), ge=0, description="Frais appliqués")
    total_to_pay: Decimal = Field(..., gt=0, description="Montant total à payer")
    
    notes: Optional[str] = Field(None, max_length=255, description="Notes additionnelles")

    @field_validator('sender_currency', 'receiver_currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Valide que la devise est en majuscules"""
        return v.upper()


class TransferUpdate(BaseSchema):
    """Schema pour mettre à jour une transaction"""
    status: Optional[TransactionStatus] = None
    notes: Optional[str] = Field(None, max_length=255)
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None


class TransferResponse(BaseSchema, IDMixin, TimestampMixin):
    """Schema de réponse pour une transaction"""
    timestamp: datetime
    reference: str
    
    sender_country: str
    receiver_country: str
    sender_partner: str
    receiver_partner: str
    
    sender_id: UUID
    receiver_full_name: str
    receiver_phone: str
    receiver_email: Optional[str] = None
    
    sender_amount: Decimal
    sender_currency: str
    receiver_amount: Decimal
    receiver_currency: str
    exchange_rate: Decimal
    
    applied_fee: Decimal
    total_to_pay: Decimal
    
    status: TransactionStatus
    notes: Optional[str] = None
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None


class TransferWithSender(TransferResponse):
    """Schema de réponse avec les détails de l'expéditeur"""
    sender: UserResponse


class TransferStatusUpdate(BaseSchema):
    """Schema pour mettre à jour le statut d'une transaction"""
    status: TransactionStatus = Field(..., description="Nouveau statut de la transaction")
    notes: Optional[str] = Field(None, max_length=255, description="Notes additionnelles")


class TransferFilter(BaseSchema):
    """Schema pour filtrer les transactions"""
    sender_id: Optional[UUID] = None
    status: Optional[TransactionStatus] = None
    sender_country: Optional[str] = None
    receiver_country: Optional[str] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
# ============== Schema pour un devis de transfer ===========


class TransferQuoteRequest(BaseSchema):
    """Schema pour demander un devis de transfert"""
    sender_country: str = Field(..., min_length=2, description="Pays d'envoi")
    receiver_country: str = Field(..., min_length=2, description="Pays de réception")
    sender_currency: str = Field(..., min_length=3, max_length=3, description="Devise d'envoi")
    receiver_currency: str = Field(..., min_length=3, max_length=3, description="Devise de réception")
    amount: Decimal = Field(..., gt=0, description="Montant à envoyer")
    
    @field_validator('sender_currency', 'receiver_currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Convertit la devise en majuscules"""
        return v.upper()


class TransferQuoteResponse(BaseSchema):
    """Schema de réponse pour un devis de transfert"""
    # Informations de base
    sender_country: str
    receiver_country: str
    sender_currency: str
    receiver_currency: str
    corridor: str
    
    # Montants
    sender_amount: Decimal = Field(..., description="Montant à envoyer")
    exchange_rate: Decimal = Field(..., description="Taux de change appliqué")
    fee_amount: Decimal = Field(..., description="Montant des frais")
    fee_percentage: Optional[Decimal] = Field(None, description="Pourcentage des frais")
    total_to_pay: Decimal = Field(..., description="Montant total à payer")
    receiver_amount: Decimal = Field(..., description="Montant que recevra le bénéficiaire")
    
    # Métadonnées
    fee_type: str = Field(..., description="Type de frais appliqué")
    is_available: bool = Field(default=True, description="Indique si le transfert est disponible")
    message: Optional[str] = Field(None, description="Message additionnel")


class TransferCalculation(BaseSchema):
    """Schema pour les calculs internes de transfert"""
    base_amount: Decimal
    exchange_rate: Decimal
    converted_amount: Decimal
    fee_amount: Decimal
    total_amount: Decimal
