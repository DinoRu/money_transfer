"""
Modèle Country pour gérer les pays
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from src.models.base import BaseModel


class Country(BaseModel):
    """Modèle pour les pays"""
    
    __tablename__ = "countries"
    
    # Code ISO 3166-1 alpha-2 (CI, SN, RU, etc.)
    code = Column(String(2), unique=True, index=True, nullable=False)
    
    # Noms
    name = Column(String(100), nullable=False)  # Nom en anglais
   
    # Emoji drapeau
    flag = Column(String(10), nullable=False)
    
    # Devise
    currency_id = Column(UUID(as_uuid=True), ForeignKey("currencies.id"), nullable=False)
    
    # Code téléphonique
    dial_code = Column(String(10), nullable=False)
    
    # Longueur du numéro de téléphone (sans dial_code)
    phone_number_length = Column(Integer, nullable=False, default=9)
    
    # Exemple de format de téléphone
    phone_format_example = Column(String(50), nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Pour l'envoi ou la réception
    can_send_from = Column(Boolean, default=True, nullable=False)
    can_send_to = Column(Boolean, default=True, nullable=False)
    
    # Ordre d'affichage
    display_order = Column(Integer, default=0, nullable=False)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Relations
    currency = relationship("Currency", back_populates="countries", lazy="selectin")
    payment_partners = relationship(
        "PaymentPartner",
        back_populates="country",
        lazy="dynamic"
    )
    
     # ✅ Relations Fee
    fee_from = relationship(
        "Fee",
        foreign_keys="Fee.from_country_id",
        back_populates="from_country",
        lazy="selectin"
    )

    fee_to = relationship(
        "Fee",
        foreign_keys="Fee.to_country_id",
        back_populates="to_country",
        lazy="selectin"
    )

    
    def __repr__(self):
        return f"<Country(code={self.code}, name={self.name_fr})>"
    
    @property
    def display_name(self) -> str:
        """Nom d'affichage avec drapeau"""
        return f"{self.flag} {self.name_fr}"
    
    @property
    def phone_code(self) -> str:
        """Code téléphonique avec +"""
        return self.dial_code
    
    @property
    def numeric_phone_code(self) -> str:
        """Code téléphonique sans +"""
        return self.dial_code.replace('+', '')