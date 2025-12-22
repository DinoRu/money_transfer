from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_utils import Currency as CurrencyType
from sqlmodel import select, func

from src.auth.permission import admin_required
from src.db.models import Currency
from src.db.session import get_session
from src.schemas.currency import (
    CurrencyModel,
    CurrencyCreate,
    CurrencyUpdate,
    CurrencyList,
)
from src.schemas.common import SuccessResponse

router = APIRouter()


# ============================================
# DEPENDENCY FUNCTIONS
# ============================================

async def get_currency_or_404(
    currency_id: UUID,
    session: AsyncSession = Depends(get_session)
) -> Currency:
    """Get currency by ID or raise 404"""
    stmt = select(Currency).where(Currency.id == currency_id)
    result = await session.execute(stmt)
    currency = result.scalar_one_or_none()
    
    if not currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devise avec l'ID {currency_id} non trouvée"
        )
    
    return currency


async def validate_currency_code(code: str, session: AsyncSession) -> None:
    """Validate that a currency code doesn't already exist"""
    stmt = select(Currency).where(Currency.code == code.upper())
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La devise avec le code '{code}' existe déjà"
        )


# ============================================
# CRUD ENDPOINTS
# ============================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CurrencyModel,
    dependencies=[Depends(admin_required)]
)
async def create_currency(
    currency_schema: CurrencyCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Créer une nouvelle devise à partir d'un code ISO 4217.
    
    La devise sera automatiquement enrichie avec:
    - Le nom complet
    - Le symbole
    
    Exemple: Code "USD" → name: "US Dollar", symbol: "$"
    """
    # Validate currency code doesn't exist
    await validate_currency_code(currency_schema.code, session)
    
    try:
        # Get currency information from ISO standard
        currency_type = CurrencyType(currency_schema.code)
        currency_code = currency_type.code
        currency_name = currency_type.name
        currency_symbol = currency_type.symbol
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Code de devise ISO 4217 invalide: '{currency_schema.code}'"
        )
    
    # Create currency
    currency = Currency(
        code=currency_code,
        name=currency_name,
        symbol=currency_symbol
    )
    
    session.add(currency)
    await session.commit()
    await session.refresh(currency)
    
    return currency


@router.get(
    "",
    response_model=List[CurrencyModel],
    status_code=status.HTTP_200_OK
)
async def get_currencies(
    search: Optional[str] = Query(None, description="Rechercher par code ou nom"),
    code: Optional[str] = Query(None, min_length=3, max_length=3, description="Filtrer par code exact"),
    limit: int = Query(100, ge=1, le=500, description="Nombre maximum de résultats"),
    offset: int = Query(0, ge=0, description="Nombre de résultats à ignorer"),
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer toutes les devises avec options de recherche et filtrage.
    
    Paramètres:
    - search: Recherche partielle dans code ou nom
    - code: Filtre exact par code de devise
    - limit: Pagination (max 500)
    - offset: Pagination
    """
    # Build query
    stmt = select(Currency)
    
    # Apply filters
    if code:
        stmt = stmt.where(Currency.code == code.upper())
    elif search:
        search_pattern = f"%{search.upper()}%"
        stmt = stmt.where(
            (Currency.code.ilike(search_pattern)) |
            (Currency.name.ilike(search_pattern))
        )
    
    # Apply pagination and ordering
    stmt = stmt.order_by(Currency.code).offset(offset).limit(limit)
    
    result = await session.execute(stmt)
    currencies = result.scalars().all()
    
    return currencies


@router.get(
    "/count",
    response_model=dict,
    status_code=status.HTTP_200_OK
)
async def get_currencies_count(
    session: AsyncSession = Depends(get_session)
):
    """Obtenir le nombre total de devises dans le système"""
    stmt = select(func.count()).select_from(Currency)
    result = await session.execute(stmt)
    count = result.scalar_one()
    
    return {
        "total": count,
        "message": f"{count} devise(s) dans le système"
    }


@router.get(
    "/{currency_id}",
    response_model=CurrencyModel,
    status_code=status.HTTP_200_OK
)
async def get_currency(
    currency: Currency = Depends(get_currency_or_404)
):
    """Récupérer une devise par son ID"""
    return currency


@router.get(
    "/code/{currency_code}",
    response_model=CurrencyModel,
    status_code=status.HTTP_200_OK
)
async def get_currency_by_code(
    currency_code: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer une devise par son code ISO.
    
    Exemple: /code/USD pour obtenir le dollar américain
    """
    stmt = select(Currency).where(Currency.code == currency_code.upper())
    result = await session.execute(stmt)
    currency = result.scalar_one_or_none()
    
    if not currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devise '{currency_code.upper()}' non trouvée"
        )
    
    return currency


@router.patch(
    "/{currency_id}",
    response_model=CurrencyModel,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(admin_required)]
)
async def update_currency(
    update_data: CurrencyUpdate,
    currency: Currency = Depends(get_currency_or_404),
    session: AsyncSession = Depends(get_session)
):
    """
    Mettre à jour une devise existante.
    
    Note: La mise à jour du code nécessite une validation supplémentaire
    pour éviter les doublons.
    """
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # If updating code, check it doesn't already exist
    if 'code' in update_dict and update_dict['code'] != currency.code:
        await validate_currency_code(update_dict['code'], session)
    
    # Apply updates
    for key, value in update_dict.items():
        setattr(currency, key, value)
    
    session.add(currency)
    await session.commit()
    await session.refresh(currency)
    
    return currency


@router.delete(
    "/{currency_id}",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse,
    dependencies=[Depends(admin_required)]
)
async def delete_currency(
    currency: Currency = Depends(get_currency_or_404),
    session: AsyncSession = Depends(get_session)
):
    """
    Supprimer une devise.
    
    Note: Cela échouera si la devise est utilisée par des pays ou
    des transactions existantes (contrainte de clé étrangère).
    """
    try:
        await session.delete(currency)
        await session.commit()
        
        return SuccessResponse(
            message=f"Devise '{currency.code}' supprimée avec succès"
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Impossible de supprimer la devise: elle est utilisée par d'autres entités. Détails: {str(e)}"
        )


@router.delete(
    "/batch/clear",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    dependencies=[Depends(admin_required)]
)
async def delete_all_currencies(
    confirm: bool = Query(False, description="Confirmer la suppression de toutes les devises"),
    session: AsyncSession = Depends(get_session)
):
    """
    Supprimer TOUTES les devises du système.
    
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
        count_stmt = select(func.count()).select_from(Currency)
        count_result = await session.execute(count_stmt)
        total_count = count_result.scalar_one()
        
        # Delete all
        stmt = select(Currency)
        result = await session.execute(stmt)
        currencies = result.scalars().all()
        
        for currency in currencies:
            await session.delete(currency)
        
        await session.commit()
        
        return {
            "message": "Toutes les devises ont été supprimées",
            "deleted_count": total_count,
            "success": True
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Impossible de supprimer toutes les devises: {str(e)}"
        )


# ============================================
# UTILITY ENDPOINTS
# ============================================

@router.get(
    "/supported/list",
    response_model=List[dict],
    status_code=status.HTTP_200_OK
)
async def get_supported_currency_codes():
    """
    Obtenir la liste de tous les codes de devise ISO 4217 supportés.
    
    Utile pour afficher une liste de sélection dans l'app Flutter.
    Retourne uniquement les devises les plus courantes.
    """
    # List of most common currencies
    common_currencies = [
        'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD',
        'CNY', 'INR', 'BRL', 'ZAR', 'RUB', 'MXN', 'SGD', 'HKD',
        'NOK', 'SEK', 'DKK', 'PLN', 'THB', 'IDR', 'MYR', 'PHP',
        'AED', 'SAR', 'KRW', 'TRY', 'EGP', 'NGN', 'KES', 'GHS',
        'XOF', 'XAF', 'MAD', 'TND', 'DZD'
    ]
    
    result = []
    for code in common_currencies:
        try:
            currency = CurrencyType(code)
            result.append({
                'code': currency.code,
                'name': currency.name,
                'symbol': currency.symbol
            })
        except:
            continue
    
    return sorted(result, key=lambda x: x['code'])


@router.post(
    "/batch/create",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    dependencies=[Depends(admin_required)]
)
async def create_multiple_currencies(
    currency_codes: List[str],
    session: AsyncSession = Depends(get_session)
):
    """
    Créer plusieurs devises en une seule requête.
    
    Exemple de body:
    ```json
    ["USD", "EUR", "GBP", "JPY"]
    ```
    """
    created = []
    skipped = []
    errors = []
    
    for code in currency_codes:
        try:
            # Check if exists
            stmt = select(Currency).where(Currency.code == code.upper())
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                skipped.append({
                    'code': code.upper(),
                    'reason': 'Already exists'
                })
                continue
            
            # Create currency
            currency_type = CurrencyType(code.upper())
            currency = Currency(
                code=currency_type.code,
                name=currency_type.name,
                symbol=currency_type.symbol
            )
            
            session.add(currency)
            created.append(currency_type.code)
            
        except ValueError:
            errors.append({
                'code': code,
                'reason': 'Invalid ISO 4217 code'
            })
        except Exception as e:
            errors.append({
                'code': code,
                'reason': str(e)
            })
    
    await session.commit()
    
    return {
        'message': f'{len(created)} devise(s) créée(s) avec succès',
        'created': created,
        'skipped': skipped,
        'errors': errors,
        'total_created': len(created),
        'total_skipped': len(skipped),
        'total_errors': len(errors)
    }