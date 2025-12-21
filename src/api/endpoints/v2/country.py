"""
Router pour la gestion des pays (Countries)
Endpoints CRUD + pays expéditeurs/destinataires
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, require_admin, PaginationParams
from src.services import country_service
from src.schemas.country import CountryCreate, CountryUpdate, CountryResponse, CountryWithCurrency


router = APIRouter(prefix="/countries", tags=["Countries"])


@router.get("", response_model=List[CountryResponse])
async def list_countries(
    db: AsyncSession = Depends(get_db),
    pagination: PaginationParams = Depends()
):
    """
    Lister tous les pays avec pagination
    
    - **skip**: Nombre d'éléments à sauter
    - **limit**: Nombre max d'éléments
    """
    countries = await country_service.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return countries


@router.get("/with-currencies", response_model=List[CountryWithCurrency])
async def list_countries_with_currencies(db: AsyncSession = Depends(get_db)):
    """
    Lister tous les pays avec leurs devises
    
    Utile pour affichage complet
    """
    countries = await country_service.get_all_with_currencies(db)
    return countries


@router.get("/senders", response_model=List[CountryWithCurrency])
async def list_sender_countries(db: AsyncSession = Depends(get_db)):
    """
    Lister les pays depuis lesquels on peut envoyer de l'argent
    
    Filtre: can_send_from = true
    """
    countries = await country_service.get_sender_countries(db)
    return countries


@router.get("/receivers", response_model=List[CountryWithCurrency])
async def list_receiver_countries(db: AsyncSession = Depends(get_db)):
    """
    Lister les pays vers lesquels on peut envoyer de l'argent
    
    Filtre: can_send_to = true
    """
    countries = await country_service.get_receiver_countries(db)
    return countries


@router.get("/search", response_model=List[CountryResponse])
async def search_countries(
    q: str = Query(..., min_length=1, description="Terme de recherche"),
    db: AsyncSession = Depends(get_db),
    pagination: PaginationParams = Depends()
):
    """
    Rechercher des pays par nom
    
    - **q**: Terme de recherche (min 1 caractère)
    """
    results = await country_service.search(
        db,
        "name",
        q,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return results


@router.get("/code/{code}", response_model=CountryWithCurrency)
async def get_country_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer un pays par son code ISO
    
    - **code**: Code ISO du pays (ex: FR, CI, SN)
    """
    country = await country_service.get_by_code(db, code.upper())
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pays {code} non trouvé"
        )
    
    return country


@router.get("/stats", response_model=dict)
async def get_country_statistics(db: AsyncSession = Depends(get_db)):
    """
    Obtenir les statistiques sur les pays
    
    Returns:
        - total_countries: Nombre total
        - sender_countries: Pays expéditeurs
        - receiver_countries: Pays destinataires
    """
    total = await country_service.count(db)
    senders = len(await country_service.get_sender_countries(db))
    receivers = len(await country_service.get_receiver_countries(db))
    
    return {
        "total_countries": total,
        "sender_countries": senders,
        "receiver_countries": receivers
    }


@router.get("/{country_id}", response_model=CountryWithCurrency)
async def get_country(
    country_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer un pays par son ID avec sa devise
    
    - **country_id**: UUID du pays
    """
    country = await country_service.get_with_currency(db, country_id)
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pays non trouvé"
        )
    
    return country


@router.post("", response_model=CountryResponse, status_code=status.HTTP_201_CREATED)
async def create_country(
    country_data: CountryCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Créer un nouveau pays
    
    - **name**: Nom du pays
    - **code**: Code ISO (2 lettres en majuscules)
    - **currency_id**: UUID de la devise du pays
    - **can_send_from**: Peut envoyer depuis ce pays
    - **can_send_to**: Peut envoyer vers ce pays
    
    Requires: Role ADMIN
    """
    try:
        country = await country_service.create(db, country_data)
        await db.commit()
        return country
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{country_id}", response_model=CountryResponse)
async def update_country(
    country_id: UUID,
    country_data: CountryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Mettre à jour un pays
    
    - **country_id**: UUID du pays
    
    Requires: Role ADMIN
    """
    country = await country_service.update(db, country_id, country_data)
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pays non trouvé"
        )
    
    await db.commit()
    return country


@router.delete("/{country_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_country(
    country_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Supprimer un pays
    
    - **country_id**: UUID du pays
    
    Note: Ne peut être supprimé si utilisé par des frais ou partenaires
    
    Requires: Role ADMIN
    """
    deleted = await country_service.delete(db, country_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pays non trouvé"
        )
    
    await db.commit()
    return None