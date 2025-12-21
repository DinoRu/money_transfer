"""
Énumérations utilisées dans les modèles
"""
import enum


class UserRole(str, enum.Enum):
    ADMIN = 'admin'
    USER = 'user'
    AGENT = 'agent'
   
    
class UserStatus(str, enum.Enum):
    """Statut des utilisateurs"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class PaymentPartnerType(str, enum.Enum):
    """Types de méthodes de paiement"""
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    CASH_PICKUP = "cash_pickup"
    CARD = "card"


class FeeType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"


class TransactionStatus(str, enum.Enum):
    AWAITING_PAYMENT = "En attente de paiement"
    COMPLETED = "Effectuée"
    FOUNDS_DEPOSITED = 'Dépôt confirmé'
    EXPIRED = "Expirée"
    CANCELLED = "Annulée"