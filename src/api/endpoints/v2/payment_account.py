
"""
Router pour la gestion des comptes de paiement
Endpoints CRUD + validation
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, require_admin, PaginationParams
from src.services import payment_account_service
from src.schemas.payment_account import (
    PaymentAccountCreate, PaymentAccountUpdate,
    PaymentAccountResponse, PaymentAccountWithPartner
)


router = APIRouter(prefix="/payment-accounts", tags=["Payment Accounts"])


@router.get("", response_model=List[PaymentAccountResponse])
async def list_payment_accounts(
    db: AsyncSession = Depends(get_db),
    pagination: PaginationParams = Depends()
):
    """
    Lister tous les comptes de paiement
    """
    accounts = await payment_account_service.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return accounts


@router.get("/active", response_model=List[PaymentAccountResponse])
async def list_active_accounts(db: AsyncSession = Depends(get_db)):
    """
    Lister uniquement les comptes actifs
    """
    accounts = await payment_account_service.get_active(db)
    return accounts


@router.get("/partner/{partner_id}", response_model=List[PaymentAccountResponse])
async def get_accounts_by_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les comptes d'un partenaire
    
    - **partner_id**: UUID du partenaire
    """
    accounts = await payment_account_service.get_by_partner(db, partner_id)
    return accounts


@router.get("/partner/{partner_id}/active", response_model=List[PaymentAccountResponse])
async def get_active_accounts_by_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les comptes actifs d'un partenaire
    
    - **partner_id**: UUID du partenaire
    """
    accounts = await payment_account_service.get_active_by_partner(db, partner_id)
    return accounts


@router.get("/partner/{partner_id}/stats", response_model=dict)
async def get_partner_account_stats(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtenir les statistiques des comptes d'un partenaire
    
    - **partner_id**: UUID du partenaire
    
    Returns:
        - total_accounts: Nombre total
        - active_accounts: Nombre actifs
        - inactive_accounts: Nombre inactifs
        - accounts_with_number: Avec numéro
        - accounts_with_bank: Avec nom de banque
    """
    stats = await payment_account_service.get_statistics(db, partner_id)
    return stats


@router.post("/{account_id}/validate", response_model=dict)
async def validate_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Valider qu'un compte peut être utilisé pour une transaction
    
    - **account_id**: UUID du compte
    
    Returns:
        - valid: true/false
        - message: Raison si invalide
    """
    is_valid, message = await payment_account_service.validate_account_for_transaction(
        db, account_id
    )
    
    return {
        "valid": is_valid,
        "message": message or "Compte valide"
    }


@router.get("/number/{account_number}", response_model=PaymentAccountWithPartner)
async def get_account_by_number(
    account_number: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer un compte par son numéro
    
    - **account_number**: Numéro du compte
    """
    account = await payment_account_service.get_by_account_number(db, account_number)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compte non trouvé"
        )
    
    return account


@router.get("/stats", response_model=dict)
async def get_account_statistics(db: AsyncSession = Depends(get_db)):
    """
    Obtenir les statistiques globales sur les comptes
    """
    total = await payment_account_service.count(db)
    active = len(await payment_account_service.get_active(db))
    
    return {
        "total_accounts": total,
        "active_accounts": active,
        "inactive_accounts": total - active
    }


@router.get("/{account_id}", response_model=PaymentAccountWithPartner)
async def get_payment_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer un compte par son ID
    """
    account = await payment_account_service.get_with_partner(db, account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compte non trouvé"
        )
    
    return account


@router.post("", response_model=PaymentAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_account(
    account_data: PaymentAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Créer un nouveau compte de paiement
    
    - **payment_partner_id**: UUID du partenaire
    - **account_name**: Nom du compte
    - **account_number**: Numéro du compte (unique)
    - **bank_name**: Nom de la banque (optionnel)
    - **is_active**: Actif ou non
    
    Requires: Role ADMIN
    """
    try:
        account = await payment_account_service.create(db, account_data)
        await db.commit()
        return account
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{account_id}", response_model=PaymentAccountResponse)
async def update_payment_account(
    account_id: UUID,
    account_data: PaymentAccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Mettre à jour un compte de paiement
    
    Requires: Role ADMIN
    """
    account = await payment_account_service.update(db, account_id, account_data)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compte non trouvé"
        )
    
    await db.commit()
    return account


@router.patch("/{account_id}/activate", response_model=PaymentAccountResponse)
async def activate_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Activer un compte
    
    Requires: Role ADMIN
    """
    account = await payment_account_service.activate(db, account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compte non trouvé"
        )
    
    await db.commit()
    return account


@router.patch("/{account_id}/deactivate", response_model=PaymentAccountResponse)
async def deactivate_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Désactiver un compte
    
    Requires: Role ADMIN
    """
    account = await payment_account_service.deactivate(db, account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compte non trouvé"
        )
    
    await db.commit()
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Supprimer un compte
    
    Requires: Role ADMIN
    """
    deleted = await payment_account_service.delete(db, account_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compte non trouvé"
        )
    
    await db.commit()
    return None
