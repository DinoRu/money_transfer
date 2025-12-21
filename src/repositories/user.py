"""
Repository pour le modèle User en mode asynchrone
"""
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.models.enums import UserRole
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository pour gérer les utilisateurs"""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """
        Récupère un utilisateur par son email
        
        Args:
            db: Session asynchrone
            email: Email de l'utilisateur
            
        Returns:
            L'utilisateur ou None
        """
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[User]:
        """
        Récupère un utilisateur par son téléphone
        
        Args:
            db: Session asynchrone
            phone: Numéro de téléphone
            
        Returns:
            L'utilisateur ou None
        """
        result = await db.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none()
    
    async def get_by_role(
        self,
        db: AsyncSession,
        role: UserRole,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Récupère les utilisateurs par rôle
        
        Args:
            db: Session asynchrone
            role: Rôle des utilisateurs
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste d'utilisateurs
        """
        result = await db.execute(
            select(User)
            .where(User.role == role.value)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_admins(self, db: AsyncSession) -> List[User]:
        """
        Récupère tous les administrateurs
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des administrateurs
        """
        result = await db.execute(
            select(User).where(User.role == UserRole.ADMIN.value)
        )
        return list(result.scalars().all())
    
    async def get_agents(self, db: AsyncSession) -> List[User]:
        """
        Récupère tous les agents
        
        Args:
            db: Session asynchrone
            
        Returns:
            Liste des agents
        """
        result = await db.execute(
            select(User).where(User.role == UserRole.AGENT.value)
        )
        return list(result.scalars().all())
    
    async def email_exists(
        self,
        db: AsyncSession,
        email: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Vérifie si un email existe déjà
        
        Args:
            db: Session asynchrone
            email: Email à vérifier
            exclude_id: ID à exclure de la vérification
            
        Returns:
            True si l'email existe
        """
        query = select(User).where(User.email == email)
        if exclude_id:
            query = query.where(User.id != exclude_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def phone_exists(
        self,
        db: AsyncSession,
        phone: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Vérifie si un téléphone existe déjà
        
        Args:
            db: Session asynchrone
            phone: Téléphone à vérifier
            exclude_id: ID à exclure de la vérification
            
        Returns:
            True si le téléphone existe
        """
        query = select(User).where(User.phone == phone)
        if exclude_id:
            query = query.where(User.id != exclude_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def search_users(
        self,
        db: AsyncSession,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Recherche des utilisateurs par nom, email ou téléphone
        
        Args:
            db: Session asynchrone
            query: Terme de recherche
            skip: Nombre à sauter
            limit: Limite de résultats
            
        Returns:
            Liste d'utilisateurs correspondants
        """
        search_pattern = f"%{query}%"
        result = await db.execute(
            select(User)
            .where(
                or_(
                    User.full_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.phone.ilike(search_pattern)
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


# Instance globale du repository
user_repository = UserRepository()