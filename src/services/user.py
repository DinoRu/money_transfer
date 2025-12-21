"""
Service pour les utilisateurs en mode asynchrone
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from src.models import User
from src.models.enums import UserRole
from src.repositories import user_repository
from src.schemas.user import UserCreate, UserUpdate, UserResponse
from .base import BaseService


# Configuration pour le hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService(BaseService[User, UserCreate, UserUpdate, UserResponse]):
    """Service pour la gestion des utilisateurs"""
    
    def __init__(self):
        super().__init__(user_repository, UserResponse)
    
    # ========================================
    # Méthodes spécifiques aux utilisateurs
    # ========================================
    
    async def create(self, db: AsyncSession, obj_in: UserCreate) -> UserResponse:
        """
        Crée un nouvel utilisateur avec validation et hachage du mot de passe
        
        Args:
            db: Session asynchrone
            obj_in: Données de l'utilisateur
            
        Returns:
            L'utilisateur créé
            
        Raises:
            ValueError: Si l'email ou le téléphone existe déjà
        """
        # Vérifier l'unicité de l'email
        if await self.repository.email_exists(db, obj_in.email):
            raise ValueError(f"L'email {obj_in.email} est déjà utilisé")
        
        # Vérifier l'unicité du téléphone
        if await self.repository.phone_exists(db, obj_in.phone):
            raise ValueError(f"Le numéro {obj_in.phone} est déjà utilisé")
        
        # Préparer les données
        obj_data = obj_in.model_dump(exclude={"password"})
        # Hacher le mot de passe
        obj_data['hashed_password'] = self.hash_password(obj_in.password)
        
        # Créer l'utilisateur
        user = await self.repository.create(db, obj_data)
        return UserResponse.model_validate(user)
    
    async def update(
        self,
        db: AsyncSession,
        id: UUID,
        obj_in: UserUpdate
    ) -> Optional[UserResponse]:
        """
        Met à jour un utilisateur avec validation
        
        Args:
            db: Session asynchrone
            id: UUID de l'utilisateur
            obj_in: Nouvelles données
            
        Returns:
            L'utilisateur mis à jour ou None
            
        Raises:
            ValueError: Si l'email ou le téléphone existe déjà
        """
        user = await self.repository.get(db, id)
        if not user:
            return None
        
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Vérifier l'unicité de l'email si modifié
        if 'email' in update_data:
            if await self.repository.email_exists(db, update_data['email'], exclude_id=id):
                raise ValueError(f"L'email {update_data['email']} est déjà utilisé")
        
        # Vérifier l'unicité du téléphone si modifié
        if 'phone' in update_data:
            if await self.repository.phone_exists(db, update_data['phone'], exclude_id=id):
                raise ValueError(f"Le numéro {update_data['phone']} est déjà utilisé")
        
        # Hacher le nouveau mot de passe si fourni
        if 'password' in update_data and update_data['password']:
            update_data['password'] = self.hash_password(update_data['password'])
        
        updated_user = await self.repository.update(db, user, update_data)
        return UserResponse.model_validate(updated_user)
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[UserResponse]:
        """
        Récupère un utilisateur par email
        
        Args:
            db: Session asynchrone
            email: Email de l'utilisateur
            
        Returns:
            L'utilisateur ou None
        """
        user = await self.repository.get_by_email(db, email)
        if user:
            return UserResponse.model_validate(user)
        return None
    
    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[UserResponse]:
        """
        Récupère un utilisateur par téléphone
        
        Args:
            db: Session asynchrone
            phone: Numéro de téléphone
            
        Returns:
            L'utilisateur ou None
        """
        user = await self.repository.get_by_phone(db, phone)
        if user:
            return UserResponse.model_validate(user)
        return None
    
    async def get_by_role(
        self,
        db: AsyncSession,
        role: UserRole,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserResponse]:
        """
        Récupère les utilisateurs par rôle
        
        Args:
            db: Session asynchrone
            role: Rôle à filtrer
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des utilisateurs
        """
        users = await self.repository.get_by_role(db, role, skip, limit)
        return [UserResponse.model_validate(u) for u in users]
    
    async def get_admins(self, db: AsyncSession) -> List[UserResponse]:
        """Récupère tous les administrateurs"""
        users = await self.repository.get_admins(db)
        return [UserResponse.model_validate(u) for u in users]
    
    async def get_agents(self, db: AsyncSession) -> List[UserResponse]:
        """Récupère tous les agents"""
        users = await self.repository.get_agents(db)
        return [UserResponse.model_validate(u) for u in users]
    
    async def search_users(
        self,
        db: AsyncSession,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserResponse]:
        """
        Recherche des utilisateurs
        
        Args:
            db: Session asynchrone
            query: Terme de recherche
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste des utilisateurs correspondants
        """
        users = await self.repository.search_users(db, query, skip, limit)
        return [UserResponse.model_validate(u) for u in users]
    
    async def authenticate(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authentifie un utilisateur
        
        Args:
            db: Session asynchrone
            email: Email de l'utilisateur
            password: Mot de passe en clair
            
        Returns:
            L'utilisateur si authentifié, None sinon
        """
        user = await self.repository.get_by_email(db, email)
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    async def change_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change le mot de passe d'un utilisateur
        
        Args:
            db: Session asynchrone
            user_id: UUID de l'utilisateur
            old_password: Ancien mot de passe
            new_password: Nouveau mot de passe
            
        Returns:
            True si le changement a réussi
            
        Raises:
            ValueError: Si l'ancien mot de passe est incorrect
        """
        user = await self.repository.get(db, user_id)
        if not user:
            raise ValueError("Utilisateur non trouvé")
        
        if not self.verify_password(old_password, user.password):
            raise ValueError("Ancien mot de passe incorrect")
        
        user.password = self.hash_password(new_password)
        await db.flush()
        await db.refresh(user)
        
        return True
    
    async def reset_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        new_password: str
    ) -> bool:
        """
        Réinitialise le mot de passe (admin uniquement)
        
        Args:
            db: Session asynchrone
            user_id: UUID de l'utilisateur
            new_password: Nouveau mot de passe
            
        Returns:
            True si la réinitialisation a réussi
        """
        user = await self.repository.get(db, user_id)
        if not user:
            raise ValueError("Utilisateur non trouvé")
        
        user.password = self.hash_password(new_password)
        await db.flush()
        await db.refresh(user)
        
        return True
    
    # ========================================
    # Utilitaires pour les mots de passe
    # ========================================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hache un mot de passe"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Vérifie un mot de passe"""
        return pwd_context.verify(plain_password, hashed_password)


# Instance globale du service
user_service = UserService()