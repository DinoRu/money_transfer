"""
Modèle User pour l'authentification
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, DateTime, Integer, String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from src.models.base import BaseModel
# from src.utils.utils_phone import get_dial_code


class UserRole(str, enum.Enum):
    """Rôles des utilisateurs"""
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    USER = "user"
    AGENT = "agent"


class UserStatus(str, enum.Enum):
    """Statut des utilisateurs"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(BaseModel):
    """Modèle utilisateur"""
    
    __tablename__ = "users"
    
    # Informations de base
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    # country_code = Column(String(2), nullable=False)
    
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    pin_hash = Column(String(255), nullable=True)
    
    # Biométrie
    # biometric_enabled = Column(Boolean, nullable=False, default=False)
    # biometric_public_key = Column(String(500), nullable=True)
    
    # Rôle et statut
    role = Column(
        SQLEnum(UserRole, native_enum=False, length=20),
        default=UserRole.USER,
        nullable=False
    )
    status = Column(
        SQLEnum(UserStatus, native_enum=False, length=20),
        default=UserStatus.PENDING,
        nullable=False
    )
    profile_picture_url = Column(String(500), nullable=True)
    
    # Flags
    # is_phone_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # phone_verified_at = Column(DateTime, nullable=True)
    
    # Préférences
    # preferred_language = Column(String(10), default="fr", nullable=False)
    
    # Relations
    transfers_sent = relationship(
        "Transfer",
        back_populates="sender",
        foreign_keys="Transfer.sender_id",
        lazy="dynamic"
    )
    # user_promotions = relationship("UserPromotion", back_populates="user", lazy="dynamic", cascade="all, delete-orphan", foreign_keys="UserPromotion.user_id")
    
    
    
    # failed_pin_attempts = Column(Integer, default=0, nullable=False)
    # locked_until = Column(DateTime, nullable=True, )
    
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """Vérifier si l'utilisateur est admin"""
        return self.role == UserRole.ADMIN or self.is_superuser
    
    @property
    def is_agent(self) -> bool:
        """Vérifier si l'utilisateur est agent"""
        return self.role == UserRole.AGENT
    
    # @property
    # def is_verified(self) -> bool:
    #     """Vérifier si l'utilisateur est complètement vérifié"""
    #     return self.is_phone_verified
    
    @property
    def is_locked(self) -> bool:
        """Vérifier si le compte est temporairement bloqué"""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False
    
    # @property
    # def full_phone(self) -> str:
    #     """Obtenir le numéro de téléphone complet avec indicatif"""
    #     dial_code = get_dial_code(self.country_code)
    #     return f"{dial_code}{self.phone}"
    
    def reset_failed_attempts(self) -> None:
        """Réinitialiser le compteur de tentatives échouées"""
        self.failed_pin_attempts = 0
        self.locked_until = None
    
    def increment_failed_attempts(self) -> None:
        """Incrémenter le compteur de tentatives échouées"""
        self.failed_pin_attempts += 1
        
        # Bloquer temporairement après 5 tentatives
        if self.failed_pin_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)

    