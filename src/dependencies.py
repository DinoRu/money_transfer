"""
Dépendances FastAPI réutilisables en mode asynchrone
"""
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from src.db.session import get_db
from src.models import User
from src.models.enums import UserRole
from src.config import settings


# Sécurité JWT
security = HTTPBearer()


# ========================================
# JWT Token Management
# ========================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un token d'accès JWT
    
    Args:
        data: Données à encoder dans le token
        expires_delta: Durée de validité du token
        
    Returns:
        Token JWT encodé
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Crée un token de rafraîchissement
    
    Args:
        data: Données à encoder dans le token
        
    Returns:
        Token JWT de rafraîchissement
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Décode et valide un token JWT
    
    Args:
        token: Token JWT à décoder
        
    Returns:
        Payload du token
        
    Raises:
        HTTPException: Si le token est invalide
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ========================================
# Authentication Dependencies
# ========================================

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Récupère l'ID de l'utilisateur depuis le token JWT
    
    Args:
        credentials: Credentials HTTP Bearer
        
    Returns:
        UUID de l'utilisateur
        
    Raises:
        HTTPException: Si le token est invalide
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    # Vérifier le type de token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Type de token invalide"
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )
    
    try:
        return UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID utilisateur invalide dans le token"
        )


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Récupère l'utilisateur actuel depuis la base de données
    
    Args:
        user_id: ID de l'utilisateur
        db: Session asynchrone
        
    Returns:
        Utilisateur actuel
        
    Raises:
        HTTPException: Si l'utilisateur n'existe pas
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Vérifie que l'utilisateur actuel est actif
    
    Args:
        current_user: Utilisateur actuel
        
    Returns:
        Utilisateur actuel
    """
    # Si vous avez un champ is_active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur inactif"
        )
    
    return current_user


# ========================================
# Role-Based Authorization
# ========================================

class RoleChecker:
    """
    Vérificateur de rôle pour l'autorisation
    
    Usage:
        @router.get("/admin")
        async def admin_only(current_user = Depends(RoleChecker([UserRole.ADMIN]))):
            ...
    """
    
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in [role.value for role in self.allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Rôle requis: {', '.join([r.value for r in self.allowed_roles])}"
            )
        return current_user


# Shortcuts pour les rôles courants
require_admin = RoleChecker([UserRole.ADMIN])
require_agent = RoleChecker([UserRole.ADMIN, UserRole.AGENT])
require_user = RoleChecker([UserRole.ADMIN, UserRole.AGENT, UserRole.USER])


# ========================================
# Pagination
# ========================================

class PaginationParams:
    """
    Paramètres de pagination réutilisables
    
    Usage:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            items = await get_items(skip=pagination.skip, limit=pagination.limit)
    """
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Numéro de page"),
        page_size: int = Query(
            settings.DEFAULT_PAGE_SIZE,
            ge=1,
            le=settings.MAX_PAGE_SIZE,
            description="Taille de la page"
        )
    ):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size
        self.limit = page_size


# ========================================
# Common Query Parameters
# ========================================

class CommonQueryParams:
    """
    Paramètres de requête communs
    """
    
    def __init__(
        self,
        search: Optional[str] = Query(None, description="Terme de recherche"),
        sort_by: Optional[str] = Query(None, description="Champ de tri"),
        sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Ordre de tri")
    ):
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order