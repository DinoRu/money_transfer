"""
Schemas pour le modèle User
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.models.enums import UserRole
from .base import BaseSchema, IDMixin, TimestampMixin


# Schema de base
class UserBase(BaseSchema):
    full_name: str = Field(..., min_length=2, max_length=255,  description="Nom complet")
    phone: Optional[str] = Field(None, description="Numéro de telephone")
    email: EmailStr = Field(..., description="Adresse email valide")
    role: Optional[UserRole] = Field(default=UserRole.USER, description="Rôle de l'utilisateur")
    profile_picture_url: Optional[str] = Field(default=None, description="URL de la photo de profil")

# Schemas de création
class UserCreate(UserBase):
    """Schema pour créer un utilisateur"""
    password: str = Field(..., min_length=8, max_length=100, description="Mot de passe (minimum 8 caractères)")


# Schemas de mise à jour
class UserUpdate(BaseSchema):
    """Schema pour mettre à jour un utilisateur"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    profile_picture_url: Optional[str] = None


# Schemas de réponse
class UserResponse(UserBase, IDMixin, TimestampMixin):
    """Schema de réponse pour un utilisateur"""
    id: UUID = Field(..., description="ID unique de l'utilisateur")
    is_active: bool = Field(..., description="Compte actif")
    is_superuser: bool = Field(..., description="Super utilisateur")

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def is_agent(self) -> bool:
        return self.role == UserRole.AGENT


class UserWithToken(UserResponse):
    """Schema de réponse avec token FCM"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = "bearer"


class UserLogin(BaseSchema):
    """Schema pour la connexion"""
    email: EmailStr
    password: str


class UserLoginResponse(BaseSchema):
    """Schema de réponse après connexion"""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    


class TokenResponse(BaseModel):
    """Réponse avec tokens JWT"""
    access_token: str = Field(..., description="Token d'accès JWT")
    refresh_token: str = Field(..., description="Token de rafraîchissement JWT")
    token_type: str = Field("bearer", description="Type de token")
    expires_in: int = Field(..., description="Expiration en secondes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """Requête de rafraîchissement de token"""
    refresh_token: str = Field(..., description="Token de rafraîchissement")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )