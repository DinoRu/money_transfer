"""
Service pour la gestion des transferts d'argent
"""
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.enums import FeeType
from src.repositories import (
    exchange_rate_repository,
    fee_repository,
    country_repository,
    currency_repository
)
from src.schemas.transfer import TransferQuoteRequest, TransferQuoteResponse


class TransferService:
    """Service pour la gestion des transferts"""
    
    def __init__(self):
        self.exchange_rates_repo = exchange_rate_repository
        self.fee_repo = fee_repository
        self.country_repo = country_repository
        self.currency_repo = currency_repository
    
    def get_transfer_quote(
        self,
        db: Session,
        quote_request: TransferQuoteRequest
    ) -> TransferQuoteResponse:
        """
        Génère un devis de transfert avec tous les calculs
        
        Args:
            db: Session de base de données
            quote_request: Demande de devis
            
        Returns:
            Devis de transfert complet
            
        Raises:
            ValueError: Si les données sont invalides ou manquantes
        """
        # Récupération des pays
        sender_country = self.country_repo.get_by_name(db, quote_request.sender_country)
        if not sender_country:
            raise ValueError(f"Pays d'envoi '{quote_request.sender_country}' non trouvé")
        
        receiver_country = self.country_repo.get_by_name(db, quote_request.receiver_country)
        if not receiver_country:
            raise ValueError(f"Pays de réception '{quote_request.receiver_country}' non trouvé")
        
        # Validation des devises
        sender_currency = self.currency_repo.get_by_code(db, quote_request.sender_currency)
        if not sender_currency or not sender_currency.is_active:
            raise ValueError(f"Devise d'envoi {quote_request.sender_currency} non disponible")
        
        receiver_currency = self.currency_repo.get_by_code(db, quote_request.receiver_currency)
        if not receiver_currency or not receiver_currency.is_active:
            raise ValueError(f"Devise de réception {quote_request.receiver_currency} non disponible")
        
        # Vérifier que la devise du pays correspond
        if sender_country.currency_id != sender_currency.id:
            raise ValueError(
                f"La devise {quote_request.sender_currency} ne correspond pas au pays {quote_request.sender_country}"
            )
        
        if receiver_country.currency_id != receiver_currency.id:
            raise ValueError(
                f"La devise {quote_request.receiver_currency} ne correspond pas au pays {quote_request.receiver_country}"
            )
        
        # Récupération du taux de change
        exchange_rate = self.exchange_rates_repo.get_rate(
            db,
            sender_currency.id,
            receiver_currency.id
        )
        
        if not exchange_rate:
            corridor_currencies = f"{quote_request.sender_currency}-{quote_request.receiver_currency}"
            raise ValueError(f"Taux de change non disponible pour {corridor_currencies}")
        
        # Calcul du montant converti (avant frais)
        receiver_amount_before_fee = float(quote_request.amount) * exchange_rate
        
        # Récupération et calcul des frais
        fee_amount, fee_type, fee_percentage = self._calculate_fees(
            db,
            sender_country.id,
            receiver_country.id,
            quote_request.amount
        )
        
        # Calcul du montant total à payer
        total_to_pay = quote_request.amount + fee_amount
        
        # Le montant reçu reste le même (les frais sont payés par l'expéditeur)
        receiver_amount = Decimal(str(receiver_amount_before_fee))
        
        # Vérification de disponibilité du corridor
        is_available, message = self._check_corridor_availability(
            db,
            sender_country,
            receiver_country
        )
        
        corridor_currencies = f"{quote_request.sender_currency}-{quote_request.receiver_currency}"
        
        return TransferQuoteResponse(
            sender_country=quote_request.sender_country,
            receiver_country=quote_request.receiver_country,
            sender_currency=quote_request.sender_currency,
            receiver_currency=quote_request.receiver_currency,
            corridor=corridor_currencies,
            sender_amount=quote_request.amount,
            exchange_rate=Decimal(str(exchange_rate)),
            fee_amount=fee_amount,
            fee_percentage=fee_percentage,
            total_to_pay=total_to_pay,
            receiver_amount=receiver_amount,
            fee_type=fee_type,
            is_available=is_available,
            message=message
        )
    
    def _calculate_fees(
        self,
        db: Session,
        from_country_id: UUID,
        to_country_id: UUID,
        amount: Decimal
    ) -> Tuple[Decimal, str, Optional[Decimal]]:
        """
        Calcule les frais pour un transfert
        
        Args:
            db: Session de base de données
            from_country_id: ID du pays source
            to_country_id: ID du pays destination
            amount: Montant du transfert
            
        Returns:
            Tuple (montant_frais, type_frais, pourcentage_frais)
        """
        # Récupération du frais applicable
        applicable_fee = self.fee_repo.get_applicable_fee(
            db,
            from_country_id,
            to_country_id,
            amount
        )
        
        if not applicable_fee:
            # Frais par défaut si aucun frais configuré
            default_fee_percentage = Decimal("2.5")
            fee_amount = (amount * default_fee_percentage) / Decimal("100")
            return fee_amount, "PERCENTAGE", default_fee_percentage
        
        # Calcul selon le type de frais
        fee_percentage = None
        
        if applicable_fee.fee_type == FeeType.PERCENTAGE.value:
            fee_percentage = applicable_fee.fee_value
            fee_amount = (amount * fee_percentage) / Decimal("100")
            fee_type = "PERCENTAGE"
        
        elif applicable_fee.fee_type == FeeType.FIXED.value:
            fee_amount = applicable_fee.fee_value
            fee_type = "FIXED"
            # Calculer le pourcentage équivalent pour information
            if amount > 0:
                fee_percentage = (fee_amount / amount) * Decimal("100")
        
        elif applicable_fee.fee_type == FeeType.TIERED.value:
            # Pour les frais échelonnés, utiliser la valeur configurée
            fee_amount = applicable_fee.fee_value
            fee_type = "TIERED"
            if amount > 0:
                fee_percentage = (fee_amount / amount) * Decimal("100")
        
        else:
            # Fallback
            fee_amount = Decimal("0")
            fee_type = "NONE"
        
        return fee_amount, fee_type, fee_percentage
    
    def _check_corridor_availability(
        self,
        db: Session,
        sender_country,
        receiver_country
    ) -> Tuple[bool, Optional[str]]:
        """
        Vérifie la disponibilité d'un corridor de transfert
        
        Args:
            db: Session de base de données
            sender_country: Objet Country source
            receiver_country: Objet Country destination
            
        Returns:
            Tuple (disponible, message)
        """
        if not sender_country.can_send_from:
            return False, f"Les transferts depuis {sender_country.name} ne sont pas disponibles"
        
        if not receiver_country.can_send_to:
            return False, f"Les transferts vers {receiver_country.name} ne sont pas disponibles"
        
        return True, "Transfert disponible"
    
    def validate_transfer_limits(
        self,
        db: Session,
        amount: Decimal,
        sender_currency: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Valide les limites de transfert
        
        Args:
            db: Session de base de données
            amount: Montant du transfert
            sender_currency: Devise d'envoi
            
        Returns:
            Tuple (valide, message_erreur)
        """
        # Limites générales (peuvent être configurées dans la DB)
        MIN_TRANSFER = Decimal("10")
        MAX_TRANSFER = Decimal("10000")
        
        if amount < MIN_TRANSFER:
            return False, f"Le montant minimum de transfert est {MIN_TRANSFER} {sender_currency}"
        
        if amount > MAX_TRANSFER:
            return False, f"Le montant maximum de transfert est {MAX_TRANSFER} {sender_currency}"
        
        return True, None
    
    def estimate_delivery_time(
        self,
        sender_country: str,
        receiver_country: str
    ) -> str:
        """
        Estime le temps de livraison d'un transfert
        
        Args:
            sender_country: Pays d'envoi
            receiver_country: Pays de réception
            
        Returns:
            Estimation du temps de livraison
        """
        # Logique simplifiée - peut être étendue avec des règles métier
        # basées sur les partenaires de paiement, les jours fériés, etc.
        
        # Transfert domestique
        if sender_country == receiver_country:
            return "Instantané"
        
        # Transfert international
        return "Sous 24 heures"


# Instance globale du service
transfer_service = TransferService()