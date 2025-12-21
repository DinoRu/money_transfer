"""
Modèle ExchangeRate pour gérer les taux de change
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Float, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from src.models.base import BaseModel


class ExchangeRate(BaseModel):
    """
    Modèle pour les taux de change
    Gère les conversions entre devises (RUB <-> XOF, RUB <-> XAF)
    """
    
    __tablename__ = "exchange_rates"
    
    # Devise source
    from_currency_id = Column(UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False)
    # Devise cible
    to_currency_id = Column(UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False)
    # Taux de change (combien de to_currency pour 1 from_currency)
    rate = Column(Float, nullable=False)
    # Taux inversé (calculé automatiquement pour optimisation)
    # inverse_rate = Column(Float, nullable=False)
    # Statut
    is_active = Column(Boolean, default=True, nullable=False)
    # Relations
    from_currency = relationship(
        "Currency",
        foreign_keys=[from_currency_id],
        back_populates="exchange_rates_from"
    )
    to_currency = relationship(
        "Currency",
        foreign_keys=[to_currency_id],
        back_populates="exchange_rates_to"
    )
    # Contrainte d'unicité pour la paire de devises active
    __table_args__ = (
        UniqueConstraint(
            'from_currency_id', 
            'to_currency_id', 
            # 'is_current',
            name='uq_currency_pair_current'
        ),
    )
    
    def __repr__(self):
        return (
            f"<ExchangeRate("
            f"from={self.from_currency.code if self.from_currency else 'N/A'}, "
            f"to={self.to_currency.code if self.to_currency else 'N/A'}, "
            f"rate={self.rate}"
            f")>"
        )
    
    @property
    def is_valid(self) -> bool:
        """Vérifier si le taux est valide"""
        if not self.is_active or not self.is_current:
            return False
        
        now = datetime.utcnow()
        
        if self.valid_until and self.valid_until < now:
            return False
        
        return True
    
    def calculate_exchange(self, amount: float, apply_markup: bool = True) -> float:
        """
        Calculer le montant converti
        
        Args:
            amount: Montant à convertir
            apply_markup: Appliquer le markup ou non
        
        Returns:
            Montant converti
        """
        rate_to_use = self.effective_rate if apply_markup else self.rate
        return amount * rate_to_use
    
    @staticmethod
    def calculate_effective_rate(base_rate: float, markup_percentage: float) -> float:
        """
        Calculer le taux effectif avec markup
        
        Args:
            base_rate: Taux de base
            markup_percentage: Markup en pourcentage
        
        Returns:
            Taux effectif
        """
        return base_rate * (1 - markup_percentage / 100)