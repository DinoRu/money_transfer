
"""
Router pour la gestion des utilisateurs (Users)
Endpoints CRUD + recherche
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_active_user, require_admin, PaginationParams
from src.services import user_service
from src.schemas.user import UserCreate, UserUpdate, UserResponse
from src.models.enums import UserRole


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
    pagination: PaginationParams = Depends()
):
    """
    Lister tous les utilisateurs
    
    Requires: Role ADMIN
    """
    users = await user_service.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return users


@router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=1, description="Terme de recherche"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
    pagination: PaginationParams = Depends()
):
    """
    Rechercher des utilisateurs par nom, email ou téléphone
    
    Requires: Role ADMIN
    """
    users = await user_service.search_users(
        db,
        q,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return users


@router.get("/admins", response_model=List[UserResponse])
async def list_admins(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Lister tous les administrateurs
    
    Requires: Role ADMIN
    """
    admins = await user_service.get_admins(db)
    return admins


@router.get("/agents", response_model=List[UserResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Lister tous les agents
    
    Requires: Role ADMIN
    """
    agents = await user_service.get_agents(db)
    return agents


@router.get("/role/{role}", response_model=List[UserResponse])
async def get_users_by_role(
    role: UserRole,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
    pagination: PaginationParams = Depends()
):
    """
    Récupérer les utilisateurs par rôle
    
    - **role**: ADMIN, AGENT, ou USER
    
    Requires: Role ADMIN
    """
    users = await user_service.get_by_role(
        db,
        role,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return users


@router.get("/stats", response_model=dict)
async def get_user_statistics(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Obtenir les statistiques sur les utilisateurs
    
    Requires: Role ADMIN
    """
    total = await user_service.count(db)
    active = len(await user_service.get_active(db, limit=10000))
    admins = len(await user_service.get_admins(db))
    agents = len(await user_service.get_agents(db))
    
    return {
        "total_users": total,
        "active_users": active,
        "inactive_users": total - active,
        "admins": admins,
        "agents": agents,
        "regular_users": total - admins - agents
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Récupérer un utilisateur par son ID
    
    Note: Un utilisateur ne peut voir que son propre profil,
    sauf si ADMIN
    """
    # Vérifier les permissions
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez voir que votre propre profil"
        )
    
    user = await user_service.get(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Créer un nouvel utilisateur
    
    Requires: Role ADMIN
    """
    try:
        user = await user_service.create(db, user_data)
        await db.commit()
        return user
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Mettre à jour un utilisateur
    
    Note: Un utilisateur peut mettre à jour son profil,
    sauf le rôle (ADMIN uniquement)
    """
    # Vérifier les permissions
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez modifier que votre propre profil"
        )
    
    # Empêcher la modification du rôle par un non-admin
    if current_user.role != UserRole.ADMIN and user_data.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un admin peut modifier le rôle"
        )
    
    try:
        user = await user_service.update(db, user_id, user_data)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        await db.commit()
        return user
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Activer un utilisateur
    
    Requires: Role ADMIN
    """
    user = await user_service.activate(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    await db.commit()
    return user


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Désactiver un utilisateur
    
    Requires: Role ADMIN
    """
    user = await user_service.deactivate(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    await db.commit()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Supprimer un utilisateur
    
    Requires: Role ADMIN
    """
    # Empêcher la suppression de soi-même
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas supprimer votre propre compte"
        )
    
    deleted = await user_service.delete(db, user_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    await db.commit()
    return None