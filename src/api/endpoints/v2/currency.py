"""
Router pour les devises en mode asynchrone
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, PaginationParams, require_admin
from src.services import currency_service
from src.schemas.currency import CurrencyCreate, CurrencyUpdate, CurrencyResponse


router = APIRouter(prefix="/currencies", tags=["Currencies"])


@router.post("", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
async def create_currency(
    currency_in: CurrencyCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Créer une nouvelle devise (Admin uniquement)
    """
    try:
        return await currency_service.create(db, currency_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[CurrencyResponse])
async def list_currencies(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Lister toutes les devises
    """
    return await currency_service.get_multi(db, skip=pagination.skip, limit=pagination.limit)


@router.get("/active", response_model=List[CurrencyResponse])
async def list_active_currencies(
    db: AsyncSession = Depends(get_db)
):
    """
    Lister les devises actives
    """
    return await currency_service.get_active_currencies(db)


@router.get("/{currency_id}", response_model=CurrencyResponse)
async def get_currency(
    currency_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer une devise par ID
    """
    currency = await currency_service.get(db, currency_id)
    if not currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devise non trouvée")
    return currency


@router.get("/code/{code}", response_model=CurrencyResponse)
async def get_currency_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer une devise par code ISO
    """
    currency = await currency_service.get_by_code(db, code)
    if not currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devise non trouvée")
    return currency


@router.put("/{currency_id}", response_model=CurrencyResponse)
async def update_currency(
    currency_id: UUID,
    currency_in: CurrencyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Mettre à jour une devise (Admin uniquement)
    """
    currency = await currency_service.update(db, currency_id, currency_in)
    if not currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devise non trouvée")
    return currency


@router.post("/{currency_id}/activate", response_model=CurrencyResponse)
async def activate_currency(
    currency_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Activer une devise (Admin uniquement)
    """
    currency = await currency_service.activate(db, currency_id)
    if not currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devise non trouvée")
    return currency


@router.post("/{currency_id}/deactivate", response_model=CurrencyResponse)
async def deactivate_currency(
    currency_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Désactiver une devise (Admin uniquement)
    """
    currency = await currency_service.deactivate(db, currency_id)
    if not currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devise non trouvée")
    return currency


@router.delete("/{currency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_currency(
    currency_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Supprimer une devise (Admin uniquement)
    """
    deleted = await currency_service.delete(db, currency_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devise non trouvée")