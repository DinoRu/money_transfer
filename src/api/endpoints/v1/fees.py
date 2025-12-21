from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from sqlalchemy.orm import selectinload

from src.auth.permission import admin_required
from src.db.models import Fee, Country
from src.db.session import get_session
from src.schemas.fees import (
    FeeView,
    FeeCreate,
    FeeUpdate,
    FeeWithCountries,
    FeeCalculationRequest,
    FeeCalculationResponse,
    FeeList,
)
from src.schemas.common import SuccessResponse

router = APIRouter()


# ============================================
# DEPENDENCY FUNCTIONS
# ============================================

async def get_fee_or_404(
    fee_id: UUID,
    session: AsyncSession = Depends(get_session)
) -> Fee:
    """Get fee by ID or raise 404"""
    stmt = select(Fee).where(Fee.id == fee_id)
    result = await session.execute(stmt)
    fee = result.scalar_one_or_none()
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frais avec l'ID {fee_id} non trouvé"
        )
    
    return fee


async def validate_countries_exist(
    from_country_id: UUID,
    to_country_id: UUID,
    session: AsyncSession
) -> tuple[Country, Country]:
    """Validate that both countries exist"""
    from_stmt = select(Country).where(Country.id == from_country_id)
    to_stmt = select(Country).where(Country.id == to_country_id)
    
    from_result = await session.execute(from_stmt)
    to_result = await session.execute(to_stmt)
    
    from_country = from_result.scalar_one_or_none()
    to_country = to_result.scalar_one_or_none()
    
    if not from_country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pays source avec l'ID {from_country_id} non trouvé"
        )
    
    if not to_country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pays destination avec l'ID {to_country_id} non trouvé"
        )
    
    return from_country, to_country


async def validate_fee_not_exists(
    from_country_id: UUID,
    to_country_id: UUID,
    session: AsyncSession,
    exclude_fee_id: Optional[UUID] = None
) -> None:
    """Validate that fee doesn't already exist for this country pair"""
    stmt = select(Fee).where(
        Fee.from_country_id == from_country_id,
        Fee.to_country_id == to_country_id
    )
    
    if exclude_fee_id:
        stmt = stmt.where(Fee.id != exclude_fee_id)
    
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un frais existe déjà pour cette paire de pays"
        )


# ============================================
# CRUD ENDPOINTS
# ============================================

@router.post(
    "/",
    response_model=FeeView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_required)]
)
async def create_fee(
    fee_data: FeeCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Créer un nouveau frais entre deux pays.
    
    Types de frais supportés:
    - fixed: Montant fixe (ex: 5.00)
    - percentage: Pourcentage (ex: 2.5 pour 2.5%)
    
    Validation:
    - Les deux pays doivent exister
    - Pas de doublon pour la même paire de pays
    - Fee doit être positif
    - Si percentage, doit être entre 0 et 100
    """
    # Validate countries exist
    await validate_countries_exist(
        fee_data.from_country_id,
        fee_data.to_country_id,
        session
    )
    
    # Validate no duplicate
    await validate_fee_not_exists(
        fee_data.from_country_id,
        fee_data.to_country_id,
        session
    )
    
    # Create fee
    fee = Fee(**fee_data.model_dump())
    session.add(fee)
    await session.commit()
    await session.refresh(fee)
    
    return fee


@router.get(
    "/",
    response_model=List[FeeView]
)
async def get_all_fees(
    from_country_id: Optional[UUID] = Query(None, description="Filtrer par pays source"),
    to_country_id: Optional[UUID] = Query(None, description="Filtrer par pays destination"),
    fee_type: Optional[str] = Query(None, description="Filtrer par type (fixed ou percentage)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer tous les frais avec options de filtrage.
    
    Paramètres:
    - from_country_id: Filtrer par pays source
    - to_country_id: Filtrer par pays destination
    - fee_type: Filtrer par type ('fixed' ou 'percentage')
    - limit: Pagination
    - offset: Pagination
    """
    stmt = select(Fee)
    
    # Apply filters
    if from_country_id:
        stmt = stmt.where(Fee.from_country_id == from_country_id)
    
    if to_country_id:
        stmt = stmt.where(Fee.to_country_id == to_country_id)
    
    if fee_type:
        if fee_type.lower() not in ['fixed', 'percentage']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fee_type doit être 'fixed' ou 'percentage'"
            )
        stmt = stmt.where(Fee.fee_type == fee_type.lower())
    
    # Apply pagination
    stmt = stmt.order_by(Fee.created_at.desc()).offset(offset).limit(limit)
    
    result = await session.execute(stmt)
    fees = result.scalars().all()
    
    return fees


@router.get(
    "/with-countries",
    response_model=List[FeeWithCountries]
)
async def get_fees_with_countries(
    from_country_id: Optional[UUID] = Query(None),
    to_country_id: Optional[UUID] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer les frais avec les détails des pays.
    
    Utile pour afficher une liste complète dans l'interface Flutter.
    """
    stmt = select(Fee)
    
    if from_country_id:
        stmt = stmt.where(Fee.from_country_id == from_country_id)
    if to_country_id:
        stmt = stmt.where(Fee.to_country_id == to_country_id)
    
    result = await session.execute(stmt)
    fees = result.scalars().all()
    
    # Load countries for each fee
    fees_with_countries = []
    for fee in fees:
        from_stmt = select(Country).where(Country.id == fee.from_country_id)
        to_stmt = select(Country).where(Country.id == fee.to_country_id)
        
        from_result = await session.execute(from_stmt)
        to_result = await session.execute(to_stmt)
        
        from_country = from_result.scalar_one_or_none()
        to_country = to_result.scalar_one_or_none()
        
        fee_data = FeeWithCountries(
            id=fee.id,
            from_country_id=fee.from_country_id,
            to_country_id=fee.to_country_id,
            fee=fee.fee,
            fee_type=fee.fee_type,
            min_amount=fee.min_amount,
            max_amount=fee.max_amount,
            created_at=fee.created_at,
            updated_at=fee.updated_at,
            from_country={
                'id': from_country.id,
                'name': from_country.name,
                'code_iso': from_country.code_iso,
                'flag_url': from_country.flag_url
            } if from_country else None,
            to_country={
                'id': to_country.id,
                'name': to_country.name,
                'code_iso': to_country.code_iso,
                'flag_url': to_country.flag_url
            } if to_country else None
        )
        fees_with_countries.append(fee_data)
    
    return fees_with_countries


@router.get(
    "/by-countries",
    response_model=FeeView
)
async def get_fee_by_countries(
    from_country_id: UUID = Query(..., description="ID du pays source"),
    to_country_id: UUID = Query(..., description="ID du pays destination"),
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer le frais pour une paire de pays spécifique.
    
    Retourne un seul frais ou une erreur 404 si non trouvé.
    """
    stmt = select(Fee).where(
        Fee.from_country_id == from_country_id,
        Fee.to_country_id == to_country_id
    )
    
    result = await session.execute(stmt)
    fee = result.scalar_one_or_none()
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun frais trouvé pour cette paire de pays"
        )
    
    return fee


@router.get(
    "/{fee_id}",
    response_model=FeeView
)
async def get_fee(
    fee: Fee = Depends(get_fee_or_404)
):
    """Récupérer un frais par son ID"""
    return fee


@router.patch(
    "/{fee_id}",
    response_model=FeeView,
    dependencies=[Depends(admin_required)]
)
async def update_fee(
    fee_data: FeeUpdate,
    fee: Fee = Depends(get_fee_or_404),
    session: AsyncSession = Depends(get_session)
):
    """
    Mettre à jour un frais existant.
    
    Validation:
    - Si la paire de pays change, vérifie qu'il n'y a pas de doublon
    - Si le type change en percentage, vérifie que fee <= 100
    """
    update_dict = fee_data.model_dump(exclude_unset=True)
    
    # Check for country pair change
    new_from = update_dict.get('from_country_id', fee.from_country_id)
    new_to = update_dict.get('to_country_id', fee.to_country_id)
    
    if (new_from != fee.from_country_id or new_to != fee.to_country_id):
        # Validate countries exist
        await validate_countries_exist(new_from, new_to, session)
        # Validate no duplicate
        await validate_fee_not_exists(new_from, new_to, session, exclude_fee_id=fee.id)
    
    # Apply updates
    for key, value in update_dict.items():
        setattr(fee, key, value)
    
    session.add(fee)
    await session.commit()
    await session.refresh(fee)
    
    return fee


@router.put(
    "/{fee_id}",
    response_model=FeeView,
    dependencies=[Depends(admin_required)]
)
async def replace_fee(
    fee_data: FeeCreate,
    fee: Fee = Depends(get_fee_or_404),
    session: AsyncSession = Depends(get_session)
):
    """
    Remplacer complètement un frais (PUT).
    
    Différence avec PATCH: tous les champs sont remplacés.
    """
    # Validate countries
    await validate_countries_exist(
        fee_data.from_country_id,
        fee_data.to_country_id,
        session
    )
    
    # Check for duplicate if countries changed
    if (fee_data.from_country_id != fee.from_country_id or 
        fee_data.to_country_id != fee.to_country_id):
        await validate_fee_not_exists(
            fee_data.from_country_id,
            fee_data.to_country_id,
            session,
            exclude_fee_id=fee.id
        )
    
    # Replace all fields
    for key, value in fee_data.model_dump().items():
        setattr(fee, key, value)
    
    session.add(fee)
    await session.commit()
    await session.refresh(fee)
    
    return fee


@router.delete(
    "/{fee_id}",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse,
    dependencies=[Depends(admin_required)]
)
async def delete_fee(
    fee: Fee = Depends(get_fee_or_404),
    session: AsyncSession = Depends(get_session)
):
    """Supprimer un frais"""
    await session.delete(fee)
    await session.commit()
    
    return SuccessResponse(
        message=f"Frais supprimé avec succès"
    )


@router.delete(
    "/batch/clear",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    dependencies=[Depends(admin_required)]
)
async def delete_all_fees(
    confirm: bool = Query(False, description="Confirmer la suppression"),
    session: AsyncSession = Depends(get_session)
):
    """
    Supprimer TOUS les frais du système.
    
    ⚠️ ATTENTION: Action irréversible!
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veuillez confirmer avec ?confirm=true"
        )
    
    count_stmt = select(func.count()).select_from(Fee)
    count_result = await session.execute(count_stmt)
    total_count = count_result.scalar_one()
    
    stmt = select(Fee)
    result = await session.execute(stmt)
    fees = result.scalars().all()
    
    for fee in fees:
        await session.delete(fee)
    
    await session.commit()
    
    return {
        "message": "Tous les frais ont été supprimés",
        "deleted_count": total_count,
        "success": True
    }


# ============================================
# FEE CALCULATION ENDPOINTS
# ============================================

@router.post(
    "/calculate",
    response_model=FeeCalculationResponse,
    status_code=status.HTTP_200_OK
)
async def calculate_fee(
    calculation: FeeCalculationRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Calculer les frais pour une transaction.
    
    Paramètres:
    - from_country_id: Pays source
    - to_country_id: Pays destination
    - amount: Montant de la transaction
    
    Retourne:
    - fee_amount: Montant du frais
    - total_amount: Montant total (amount + fee)
    - fee_type: Type de frais appliqué
    
    Exemple Flutter:
    ```dart
    final response = await http.post(
        Uri.parse('$baseUrl/fees/calculate'),
        body: jsonEncode({
            'from_country_id': fromCountryId,
            'to_country_id': toCountryId,
            'amount': 100.0
        })
    );
    ```
    """
    # Get fee for this country pair
    stmt = select(Fee).where(
        Fee.from_country_id == calculation.from_country_id,
        Fee.to_country_id == calculation.to_country_id
    )
    
    result = await session.execute(stmt)
    fee = result.scalar_one_or_none()
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun frais configuré pour cette paire de pays"
        )
    
    # Check amount bounds if configured
    if fee.min_amount and calculation.amount < fee.min_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le montant minimum est {fee.min_amount}"
        )
    
    if fee.max_amount and calculation.amount > fee.max_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le montant maximum est {fee.max_amount}"
        )
    
    # Calculate fee based on type
    if fee.fee_type == 'fixed':
        fee_amount = fee.fee
        fee_percentage = None
    else:  # percentage
        fee_amount = (calculation.amount * fee.fee) / Decimal(100)
        fee_percentage = fee.fee
    
    total_amount = calculation.amount + fee_amount
    
    return FeeCalculationResponse(
        from_country_id=calculation.from_country_id,
        to_country_id=calculation.to_country_id,
        amount=calculation.amount,
        fee_amount=fee_amount,
        fee_type=fee.fee_type,
        total_amount=total_amount,
        fee_percentage=fee_percentage
    )


@router.get(
    "/calculate/query",
    response_model=FeeCalculationResponse,
    status_code=status.HTTP_200_OK
)
async def calculate_fee_get(
    from_country_id: UUID = Query(...),
    to_country_id: UUID = Query(...),
    amount: Decimal = Query(..., gt=0),
    session: AsyncSession = Depends(get_session)
):
    """
    Calculer les frais (version GET).
    
    Même fonctionnalité que POST /calculate mais avec query parameters.
    Utile pour les appels simples depuis Flutter.
    """
    calculation = FeeCalculationRequest(
        from_country_id=from_country_id,
        to_country_id=to_country_id,
        amount=amount
    )
    
    return await calculate_fee(calculation, session)


# ============================================
# UTILITY ENDPOINTS
# ============================================

@router.get(
    "/count",
    response_model=dict
)
async def get_fees_count(
    session: AsyncSession = Depends(get_session)
):
    """Obtenir le nombre total de frais configurés"""
    stmt = select(func.count()).select_from(Fee)
    result = await session.execute(stmt)
    count = result.scalar_one()
    
    return {
        "total": count,
        "message": f"{count} frais configuré(s)"
    }


@router.get(
    "/countries/{country_id}/outgoing",
    response_model=List[FeeView]
)
async def get_outgoing_fees(
    country_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer tous les frais sortants d'un pays.
    
    Utile pour afficher les destinations disponibles depuis un pays.
    """
    stmt = select(Fee).where(Fee.from_country_id == country_id)
    result = await session.execute(stmt)
    
    return result.scalars().all()


@router.get(
    "/countries/{country_id}/incoming",
    response_model=List[FeeView]
)
async def get_incoming_fees(
    country_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """
    Récupérer tous les frais entrants vers un pays.
    
    Utile pour afficher les sources disponibles vers un pays.
    """
    stmt = select(Fee).where(Fee.to_country_id == country_id)
    result = await session.execute(stmt)
    
    return result.scalars().all()