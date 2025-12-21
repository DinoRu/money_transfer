from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, status, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from sqlalchemy.orm import selectinload

from src.auth.permission import admin_required
from src.db.models import Country, Currency
from src.db.session import get_session
from src.schemas.country import (
    CountryModel,
    CountryCreate,
    CountryUpdate,
    CountrySimple,
    CountryList,
)
from src.schemas.common import SuccessResponse

router = APIRouter()


# ============================================
# DEPENDENCY FUNCTIONS
# ============================================

async def get_country_or_404(
    country_id: UUID,
    session: AsyncSession = Depends(get_session)
) -> Country:
    """Get country by ID or raise 404"""
    stmt = select(Country).options(
        selectinload(Country.currency),
        selectinload(Country.payment_types),
        selectinload(Country.receiving_types)
    ).where(Country.id == country_id)
    
    result = await session.execute(stmt)
    country = result.scalar_one_or_none()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pays avec l'ID {country_id} non trouvé"
        )
    
    return country


async def validate_country_code(code_iso: str, session: AsyncSession) -> None:
    """Validate that a country code doesn't already exist"""
    stmt = select(Country).where(Country.code_iso == code_iso.upper())
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le pays avec le code ISO '{code_iso}' existe déjà"
        )


async def validate_currency_exists(currency_id: UUID, session: AsyncSession) -> Currency:
    """Validate that currency exists"""
    stmt = select(Currency).where(Currency.id == currency_id)
    result = await session.execute(stmt)
    currency = result.scalar_one_or_none()
    
    if not currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devise avec l'ID {currency_id} non trouvée"
        )
    
    return currency


# ============================================
# CRUD ENDPOINTS
# ============================================

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=CountryModel,
    dependencies=[Depends(admin_required)]
)
async def create_country(
    country_data: CountryCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Créer un nouveau pays.
    
    Valide que:
    - Le code ISO n'existe pas déjà
    - La devise existe
    """
    # Validate country code doesn't exist
    await validate_country_code(country_data.code_iso, session)
    
    # Validate currency exists
    await validate_currency_exists(country_data.currency_id, session)
    
    # Create country
    country = Country(**country_data.model_dump())
    session.add(country)
    await session.commit()
    
    # Reload with relationships
    stmt = select(Country).options(
        selectinload(Country.currency),
        selectinload(Country.payment_types),
        selectinload(Country.receiving_types)
    ).where(Country.id == country.id)
    
    result = await session.execute(stmt)
    country_with_relations = result.scalar_one()
    
    return country_with_relations


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=List[CountryModel]
)
async def get_countries(
    search: Optional[str] = Query(None, description="Rechercher par nom ou code ISO"),
    code_iso: Optional[str] = Query(None, min_length=2, max_length=3, description="Filtrer par code ISO exact"),
    currency_id: Optional[UUID] = Query(None, description="Filtrer par devise"),
    limit: int = Query(100, ge=1, le=500, description="Nombre maximum de résultats"),
    offset: int = Query(0, ge=0, description="Nombre de résultats à ignorer"),
    include_relations: bool = Query(True, description="Inclure les relations (devise, types de paiement)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer tous les pays avec options de recherche et filtrage.
    
    Paramètres:
    - search: Recherche partielle dans nom ou code ISO
    - code_iso: Filtre exact par code ISO
    - currency_id: Filtrer par devise
    - limit: Pagination (max 500)
    - offset: Pagination
    - include_relations: Inclure les relations (défaut: true)
    """
    # Build query with optional relationships
    if include_relations:
        stmt = select(Country).options(
            selectinload(Country.currency),
            selectinload(Country.payment_types),
            selectinload(Country.receiving_types)
        )
    else:
        stmt = select(Country)
    
    # Apply filters
    if code_iso:
        stmt = stmt.where(Country.code_iso == code_iso.upper())
    elif search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (Country.name.ilike(search_pattern)) |
            (Country.code_iso.ilike(search_pattern))
        )
    
    if currency_id:
        stmt = stmt.where(Country.currency_id == currency_id)
    
    # Apply pagination and ordering
    stmt = stmt.order_by(Country.name).offset(offset).limit(limit)
    
    result = await session.execute(stmt)
    countries = result.scalars().all()
    
    return countries


@router.get(
    "/count",
    response_model=dict,
    status_code=status.HTTP_200_OK
)
async def get_countries_count(
    currency_id: Optional[UUID] = Query(None, description="Compter uniquement pour une devise"),
    session: AsyncSession = Depends(get_session)
):
    """Obtenir le nombre total de pays dans le système"""
    stmt = select(func.count()).select_from(Country)
    
    if currency_id:
        stmt = stmt.where(Country.currency_id == currency_id)
    
    result = await session.execute(stmt)
    count = result.scalar_one()
    
    return {
        "total": count,
        "message": f"{count} pays dans le système"
    }


@router.get(
    "/{country_id}",
    response_model=CountryModel,
    status_code=status.HTTP_200_OK
)
async def get_country(
    country: Country = Depends(get_country_or_404)
):
    """Récupérer un pays par son ID"""
    return country


@router.get(
    "/code/{code_iso}",
    response_model=CountryModel,
    status_code=status.HTTP_200_OK
)
async def get_country_by_code(
    code_iso: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer un pays par son code ISO.
    
    Exemple: /code/US pour obtenir les États-Unis
    """
    stmt = select(Country).options(
        selectinload(Country.currency),
        selectinload(Country.payment_types),
        selectinload(Country.receiving_types)
    ).where(Country.code_iso == code_iso.upper())
    
    result = await session.execute(stmt)
    country = result.scalar_one_or_none()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pays avec le code '{code_iso.upper()}' non trouvé"
        )
    
    return country


@router.get(
    "/currency/{currency_id}",
    response_model=List[CountryModel],
    status_code=status.HTTP_200_OK
)
async def get_countries_by_currency(
    currency_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer tous les pays qui utilisent une devise spécifique.
    
    Utile pour afficher les pays disponibles après sélection de devise dans l'app.
    """
    # Validate currency exists
    await validate_currency_exists(currency_id, session)
    
    stmt = select(Country).options(
        selectinload(Country.currency),
        selectinload(Country.payment_types),
        selectinload(Country.receiving_types)
    ).where(Country.currency_id == currency_id).order_by(Country.name)
    
    result = await session.execute(stmt)
    countries = result.scalars().all()
    
    return countries


@router.patch(
    "/{country_id}",
    response_model=CountryModel,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(admin_required)]
)
async def update_country(
    country_update: CountryUpdate,
    country: Country = Depends(get_country_or_404),
    session: AsyncSession = Depends(get_session)
):
    """
    Mettre à jour un pays existant.
    
    Validation:
    - Si le code ISO change, vérifie qu'il n'existe pas déjà
    - Si la devise change, vérifie qu'elle existe
    """
    update_dict = country_update.model_dump(exclude_unset=True)
    
    # Validate code_iso if changing
    if 'code_iso' in update_dict and update_dict['code_iso'] != country.code_iso:
        await validate_country_code(update_dict['code_iso'], session)
    
    # Validate currency if changing
    if 'currency_id' in update_dict:
        await validate_currency_exists(update_dict['currency_id'], session)
    
    # Apply updates
    for key, value in update_dict.items():
        setattr(country, key, value)
    
    session.add(country)
    await session.commit()
    
    # Reload with relationships
    stmt = select(Country).options(
        selectinload(Country.currency),
        selectinload(Country.payment_types),
        selectinload(Country.receiving_types)
    ).where(Country.id == country.id)
    
    result = await session.execute(stmt)
    updated_country = result.scalar_one()
    
    return updated_country


@router.delete(
    "/{country_id}",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse,
    dependencies=[Depends(admin_required)]
)
async def delete_country(
    country: Country = Depends(get_country_or_404),
    session: AsyncSession = Depends(get_session)
):
    """
    Supprimer un pays.
    
    Note: Cela échouera si le pays est utilisé dans des frais,
    des taux de change ou des transactions (contrainte de clé étrangère).
    """
    try:
        country_name = country.name
        await session.delete(country)
        await session.commit()
        
        return SuccessResponse(
            message=f"Pays '{country_name}' supprimé avec succès"
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Impossible de supprimer le pays: il est utilisé par d'autres entités. Détails: {str(e)}"
        )


@router.delete(
    "/batch/clear",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    dependencies=[Depends(admin_required)]
)
async def delete_all_countries(
    confirm: bool = Query(False, description="Confirmer la suppression de tous les pays"),
    session: AsyncSession = Depends(get_session)
):
    """
    Supprimer TOUS les pays du système.
    
    ⚠️ ATTENTION: Cette action est irréversible!
    
    Nécessite confirm=true dans les query parameters.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veuillez confirmer la suppression avec ?confirm=true"
        )
    
    try:
        # Get count before deletion
        count_stmt = select(func.count()).select_from(Country)
        count_result = await session.execute(count_stmt)
        total_count = count_result.scalar_one()
        
        # Delete all
        stmt = select(Country)
        result = await session.execute(stmt)
        countries = result.scalars().all()
        
        for country in countries:
            await session.delete(country)
        
        await session.commit()
        
        return {
            "message": "Tous les pays ont été supprimés",
            "deleted_count": total_count,
            "success": True
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Impossible de supprimer tous les pays: {str(e)}"
        )


# ============================================
# UTILITY ENDPOINTS
# ============================================

@router.get(
    "/simple/list",
    response_model=List[CountrySimple],
    status_code=status.HTTP_200_OK
)
async def get_countries_simple(
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer une liste simplifiée de tous les pays (sans relations).
    
    Utile pour les dropdowns dans Flutter où vous n'avez besoin que
    de l'ID, du nom et du code ISO.
    """
    stmt = select(Country).order_by(Country.name)
    result = await session.execute(stmt)
    countries = result.scalars().all()
    
    return [
        CountrySimple(
            id=c.id,
            name=c.name,
            code_iso=c.code_iso,
            flag_url=c.flag_url
        )
        for c in countries
    ]


@router.post(
    "/batch/create",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    dependencies=[Depends(admin_required)]
)
async def create_multiple_countries(
    countries_data: List[CountryCreate],
    session: AsyncSession = Depends(get_session)
):
    """
    Créer plusieurs pays en une seule requête.
    
    Exemple de body:
    ```json
    [
      {
        "name": "United States",
        "code_iso": "US",
        "currency_id": "uuid-here",
        "flag_url": "https://..."
      },
      {
        "name": "France",
        "code_iso": "FR",
        "currency_id": "uuid-here"
      }
    ]
    ```
    """
    created = []
    skipped = []
    errors = []
    
    for country_data in countries_data:
        try:
            # Check if exists
            stmt = select(Country).where(Country.code_iso == country_data.code_iso.upper())
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                skipped.append({
                    'code_iso': country_data.code_iso.upper(),
                    'name': country_data.name,
                    'reason': 'Code ISO already exists'
                })
                continue
            
            # Validate currency exists
            currency_stmt = select(Currency).where(Currency.id == country_data.currency_id)
            currency_result = await session.execute(currency_stmt)
            currency = currency_result.scalar_one_or_none()
            
            if not currency:
                errors.append({
                    'name': country_data.name,
                    'reason': f'Currency ID {country_data.currency_id} not found'
                })
                continue
            
            # Create country
            country = Country(**country_data.model_dump())
            session.add(country)
            created.append({
                'name': country.name,
                'code_iso': country.code_iso
            })
            
        except Exception as e:
            errors.append({
                'name': country_data.name,
                'reason': str(e)
            })
    
    await session.commit()
    
    return {
        'message': f'{len(created)} pays créé(s) avec succès',
        'created': created,
        'skipped': skipped,
        'errors': errors,
        'total_created': len(created),
        'total_skipped': len(skipped),
        'total_errors': len(errors)
    }