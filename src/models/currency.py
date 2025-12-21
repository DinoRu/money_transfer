"""
Modèle Currency pour gérer les devises
"""
from sqlalchemy import Column, String, Boolean, Integer, Text
from sqlalchemy.orm import relationship
from src.models.base import BaseModel


class Currency(BaseModel):
    """Modèle pour les devises (XOF, XAF, RUB, etc.)"""
    
    __tablename__ = "currencies"
    
    # Code ISO 4217 (XOF, XAF, RUB)
    code = Column(String(3), unique=True, index=True, nullable=False)
    
    # Nom de la devise
    name = Column(String(100), nullable=False)
    # name_fr = Column(String(100), nullable=False)
    
    # Symbole de la devise (₽, F CFA, etc.)
    symbol = Column(String(10), nullable=False)
    
    # Zone monétaire (BCEAO, BEAC, etc.)
    # zone = Column(String(50), nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Ordre d'affichage
    display_order = Column(Integer, default=0, nullable=False)
    
    # Décimales (généralement 0 pour XOF/XAF, 2 pour RUB)
    decimal_places = Column(Integer, default=0, nullable=False)
    
    # Relations
    countries = relationship(
        "Country",
        back_populates="currency",
        lazy="dynamic"
    )
    
    exchange_rates_from = relationship(
        "ExchangeRate",
        foreign_keys="ExchangeRate.from_currency_id",
        back_populates="from_currency",
        lazy="dynamic"
    )
    
    exchange_rates_to = relationship(
        "ExchangeRate",
        foreign_keys="ExchangeRate.to_currency_id",
        back_populates="to_currency",
        lazy="dynamic"
    )
    
    def __repr__(self):
        return f"<Currency(code={self.code}, name={self.name})>"
    
    @property
    def display_name(self) -> str:
        """Nom d'affichage avec symbole"""
        return f"{self.symbol} {self.name_fr}"