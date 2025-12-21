
"""
Router pour la gestion des partenaires de paiement
Endpoints CRUD + partenaires par corridor
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, require_admin, PaginationParams
from src.services import payment_partner_service
from src.schemas.payment_partner import (
    PaymentPartnerCreate, PaymentPartnerUpdate,
    PaymentPartnerResponse, PaymentPartnerWithCountry
)
from src.models.enums import PaymentPartnerType


router = APIRouter(prefix="/payment-partners", tags=["Payment Partners"])


@router.get("", response_model=List[PaymentPartnerResponse])
async def list_payment_partners(
    db: AsyncSession = Depends(get_db),
    pagination: PaginationParams = Depends()
):
    """
    Lister tous les partenaires de paiement
    """
    partners = await payment_partner_service.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return partners


@router.get("/active", response_model=List[PaymentPartnerWithCountry])
async def list_active_partners(db: AsyncSession = Depends(get_db)):
    """
    Lister uniquement les partenaires actifs
    """
    partners = await payment_partner_service.get_active(db)
    return partners


@router.get("/country/{country_id}", response_model=List[PaymentPartnerResponse])
async def get_partners_by_country(
    country_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les partenaires d'un pays
    
    - **country_id**: UUID du pays
    """
    partners = await payment_partner_service.get_by_country(db, country_id)
    return partners


@router.get("/type/{partner_type}", response_model=List[PaymentPartnerResponse])
async def get_partners_by_type(
    partner_type: PaymentPartnerType,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les partenaires par type
    
    - **partner_type**: CARD, BANK, MOBILE_MONEY, CASH, CRYPTO
    """
    partners = await payment_partner_service.get_by_type(db, partner_type)
    return partners


@router.get("/send", response_model=List[PaymentPartnerWithCountry])
async def get_send_partners(
    country_id: Optional[UUID] = Query(None, description="Filtrer par pays"),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les partenaires pouvant envoyer
    
    - **country_id**: Optionnel - UUID du pays
    """
    partners = await payment_partner_service.get_send_partners(db, country_id)
    return partners


@router.get("/receive", response_model=List[PaymentPartnerWithCountry])
async def get_receive_partners(
    country_id: Optional[UUID] = Query(None, description="Filtrer par pays"),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les partenaires pouvant recevoir
    
    - **country_id**: Optionnel - UUID du pays
    """
    partners = await payment_partner_service.get_receive_partners(db, country_id)
    return partners


@router.get("/corridor/{sender_country_id}/{receiver_country_id}", response_model=dict)
async def get_corridor_partners(
    sender_country_id: UUID,
    receiver_country_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les partenaires disponibles pour un corridor
    
    - **sender_country_id**: UUID pays expéditeur
    - **receiver_country_id**: UUID pays destinataire
    
    Returns:
        - send_partners: Partenaires d'envoi
        - receive_partners: Partenaires de réception
        - total_send: Nombre de partenaires d'envoi
        - total_receive: Nombre de partenaires de réception
    """
    result = await payment_partner_service.get_available_for_corridor(
        db, sender_country_id, receiver_country_id
    )
    return result


@router.get("/stats", response_model=dict)
async def get_partner_statistics(db: AsyncSession = Depends(get_db)):
    """
    Obtenir les statistiques sur les partenaires
    """
    total = await payment_partner_service.count(db)
    active = len(await payment_partner_service.get_active(db))
    send = len(await payment_partner_service.get_send_partners(db))
    receive = len(await payment_partner_service.get_receive_partners(db))
    
    return {
        "total_partners": total,
        "active_partners": active,
        "inactive_partners": total - active,
        "send_partners": send,
        "receive_partners": receive
    }


@router.get("/{partner_id}", response_model=PaymentPartnerWithCountry)
async def get_payment_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer un partenaire par son ID
    """
    partner = await payment_partner_service.get_with_country(db, partner_id)
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partenaire non trouvé"
        )
    
    return partner


@router.post("", response_model=PaymentPartnerResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_partner(
    partner_data: PaymentPartnerCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Créer un nouveau partenaire de paiement
    
    Requires: Role ADMIN
    """
    try:
        partner = await payment_partner_service.create(db, partner_data)
        await db.commit()
        return partner
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{partner_id}", response_model=PaymentPartnerResponse)
async def update_payment_partner(
    partner_id: UUID,
    partner_data: PaymentPartnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Mettre à jour un partenaire
    
    Requires: Role ADMIN
    """
    partner = await payment_partner_service.update(db, partner_id, partner_data)
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partenaire non trouvé"
        )
    
    await db.commit()
    return partner


@router.patch("/{partner_id}/activate", response_model=PaymentPartnerResponse)
async def activate_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Activer un partenaire
    
    Requires: Role ADMIN
    """
    partner = await payment_partner_service.activate(db, partner_id)
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partenaire non trouvé"
        )
    
    await db.commit()
    return partner


@router.patch("/{partner_id}/deactivate", response_model=PaymentPartnerResponse)
async def deactivate_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Désactiver un partenaire
    
    Requires: Role ADMIN
    """
    partner = await payment_partner_service.deactivate(db, partner_id)
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partenaire non trouvé"
        )
    
    await db.commit()
    return partner


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_partner(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Supprimer un partenaire
    
    Requires: Role ADMIN
    """
    deleted = await payment_partner_service.delete(db, partner_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partenaire non trouvé"
        )
    
    await db.commit()
    return None