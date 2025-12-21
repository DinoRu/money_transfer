"""
Router pour la gestion des frais (Fees)
Endpoints CRUD + calcul des frais (par UUID et par code de pays)
"""
from typing import List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, require_admin, PaginationParams
from src.services import fee_service, country_service
from src.schemas.fees import (
    FeeCreate, FeeUpdate, FeeResponse, FeeWithCountries,
    FeeCalculation, FeeCalculationResponse
)


router = APIRouter(prefix="/fees", tags=["Fees"])


@router.get("", response_model=List[FeeWithCountries])
async def list_fees(
    db: AsyncSession = Depends(get_db),
    pagination: PaginationParams = Depends()
):
    """
    Lister tous les frais avec pays
    """
    fees = await fee_service.get_all_with_countries(db)
    
    # Pagination manuelle
    start = pagination.skip
    end = start + pagination.limit
    
    return fees[start:end]


@router.get("/active", response_model=List[FeeWithCountries])
async def list_active_fees(db: AsyncSession = Depends(get_db)):
    """
    Lister uniquement les frais actifs
    """
    fees = await fee_service.get_active(db)
    return fees


@router.get("/corridor/{from_country_id}/{to_country_id}", response_model=List[FeeWithCountries])
async def get_corridor_fees(
    from_country_id: UUID,
    to_country_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les frais pour un corridor spécifique (par UUID)
    
    - **from_country_id**: UUID pays source
    - **to_country_id**: UUID pays destination
    
    Returns: Liste des structures de frais (par tranches)
    """
    fees = await fee_service.get_by_corridor(db, from_country_id, to_country_id)
    return fees


@router.get("/corridor-by-code/{from_code}/{to_code}", response_model=List[FeeWithCountries])
async def get_corridor_fees_by_code(
    from_code: str,
    to_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les frais pour un corridor spécifique (par code de pays)
    
    - **from_code**: Code pays source (ex: RU, FR)
    - **to_code**: Code pays destination (ex: CI, SN)
    
    Example:
        GET /fees/corridor-by-code/RU/CI
        
        Returns: Liste des 3 tranches de frais Russie → Côte d'Ivoire
    """
    try:
        # Récupérer les pays par code
        from_country = await country_service.get_by_code(db, from_code.upper())
        if not from_country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pays {from_code} non trouvé"
            )
        
        to_country = await country_service.get_by_code(db, to_code.upper())
        if not to_country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pays {to_code} non trouvé"
            )
        
        # Récupérer les frais
        fees = await fee_service.get_by_corridor(db, from_country.id, to_country.id)
        return fees
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/calculate", response_model=FeeCalculationResponse)
async def calculate_fees(
    calculation: FeeCalculation,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculer les frais pour un transfert (par UUID)
    
    - **from_country_id**: UUID pays source
    - **to_country_id**: UUID pays destination
    - **amount**: Montant du transfert
    """
    try:
        result = await fee_service.calculate_fee(db, calculation)
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/calculate-by-code", response_model=FeeCalculationResponse)
async def calculate_fees_by_code(
    from_code: str,
    to_code: str,
    amount: float,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculer les frais pour un transfert (par code de pays)
    
    - **from_code**: Code pays source (ex: RU, FR)
    - **to_code**: Code pays destination (ex: CI, SN, ML)
    - **amount**: Montant du transfert
    
    Example:
        ```json
        {
          "from_code": "RU",
          "to_code": "CI",
          "amount": 10000
        }
        ```
        
        Returns:
        ```json
        {
          "from_country": {"name": "Russie", "code": "RU"},
          "to_country": {"name": "Côte d'Ivoire", "code": "CI"},
          "amount": 10000,
          "fee_type": "PERCENTAGE",
          "fee_value": 3.5,
          "calculated_fee": 350,
          "total_amount": 10350
        }
        ```
        
        → Frais: 350 RUB (3.5%)
        → Total à payer: 10350 RUB
    """
    try:
        # Récupérer les pays par code
        from_country = await country_service.get_by_code(db, from_code.upper())
        if not from_country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pays {from_code} non trouvé"
            )
        
        to_country = await country_service.get_by_code(db, to_code.upper())
        if not to_country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pays {to_code} non trouvé"
            )
        
        # Créer l'objet de calcul
        calculation = FeeCalculation(
            from_country_id=from_country.id,
            to_country_id=to_country.id,
            amount=Decimal(str(amount))
        )
        
        # Calculer les frais
        result = await fee_service.calculate_fee(db, calculation)
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/calculate-by-code/{from_code}/{to_code}/{amount}", response_model=FeeCalculationResponse)
async def calculate_fees_by_code_get(
    from_code: str,
    to_code: str,
    amount: float,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculer les frais pour un transfert (GET par code de pays)
    
    - **from_code**: Code pays source (ex: RU, FR)
    - **to_code**: Code pays destination (ex: CI, SN)
    - **amount**: Montant du transfert
    
    Example:
        GET /fees/calculate-by-code/RU/CI/10000
        
        Returns:
        ```json
        {
          "from_country": {"name": "Russie", "code": "RU"},
          "to_country": {"name": "Côte d'Ivoire", "code": "CI"},
          "amount": 10000,
          "fee_type": "PERCENTAGE",
          "fee_value": 3.5,
          "calculated_fee": 350,
          "total_amount": 10350
        }
        ```
    """
    try:
        # Récupérer les pays
        from_country = await country_service.get_by_code(db, from_code.upper())
        if not from_country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pays {from_code} non trouvé"
            )
        
        to_country = await country_service.get_by_code(db, to_code.upper())
        if not to_country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pays {to_code} non trouvé"
            )
        
        # Calculer
        calculation = FeeCalculation(
            from_country_id=from_country.id,
            to_country_id=to_country.id,
            amount=Decimal(str(amount))
        )
        
        result = await fee_service.calculate_fee(db, calculation)
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/estimate-total", response_model=dict)
async def estimate_total_cost(
    from_code: str,
    to_code: str,
    send_amount: float,
    db: AsyncSession = Depends(get_db)
):
    """
    Estimer le coût total d'un transfert (montant + frais)
    
    - **from_code**: Code pays source
    - **to_code**: Code pays destination
    - **send_amount**: Montant à envoyer
    
    Returns:
        - send_amount: Montant à envoyer
        - fee: Frais calculés
        - total_cost: Coût total
        - fee_percentage: Pourcentage des frais
    
    Example:
        ```json
        {
          "from_code": "FR",
          "to_code": "SN",
          "send_amount": 500
        }
        ```
        
        Returns:
        ```json
        {
          "from_country": "France",
          "to_country": "Sénégal",
          "send_amount": 500,
          "fee": 17.5,
          "total_cost": 517.5,
          "fee_percentage": 3.5
        }
        ```
    """
    try:
        # Récupérer les pays
        from_country = await country_service.get_by_code(db, from_code.upper())
        if not from_country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pays {from_code} non trouvé"
            )
        
        to_country = await country_service.get_by_code(db, to_code.upper())
        if not to_country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pays {to_code} non trouvé"
            )
        
        # Calculer les frais
        calculation = FeeCalculation(
            from_country_id=from_country.id,
            to_country_id=to_country.id,
            amount=Decimal(str(send_amount))
        )
        
        result = await fee_service.calculate_fee(db, calculation)
        
        # Calculer le pourcentage
        fee_percentage = (float(result.calculated_fee) / float(send_amount)) * 100
        
        return {
            "from_country": from_country.name,
            "to_country": to_country.name,
            "send_amount": float(send_amount),
            "fee": float(result.calculated_fee),
            "total_cost": float(result.total_amount),
            "fee_percentage": round(fee_percentage, 2),
            "fee_type": result.fee_type,
            "currency": from_country.currency.code if from_country.currency else None
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/stats", response_model=dict)
async def get_fee_statistics(db: AsyncSession = Depends(get_db)):
    """
    Obtenir les statistiques sur les frais
    """
    total = await fee_service.count(db)
    active = len(await fee_service.get_active(db))
    
    return {
        "total_fees": total,
        "active_fees": active,
        "inactive_fees": total - active
    }


@router.get("/{fee_id}", response_model=FeeWithCountries)
async def get_fee(
    fee_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer un frais par son ID avec pays
    """
    fee = await fee_service.get_with_countries(db, fee_id)
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frais non trouvé"
        )
    
    return fee


@router.post("", response_model=FeeResponse, status_code=status.HTTP_201_CREATED)
async def create_fee(
    fee_data: FeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Créer une nouvelle structure de frais
    
    Requires: Role ADMIN
    """
    try:
        fee = await fee_service.create(db, fee_data)
        await db.commit()
        return fee
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{fee_id}", response_model=FeeResponse)
async def update_fee(
    fee_id: UUID,
    fee_data: FeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Mettre à jour une structure de frais
    
    Requires: Role ADMIN
    """
    fee = await fee_service.update(db, fee_id, fee_data)
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frais non trouvé"
        )
    
    await db.commit()
    return fee


@router.patch("/{fee_id}/activate", response_model=FeeResponse)
async def activate_fee(
    fee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Activer une structure de frais
    
    Requires: Role ADMIN
    """
    fee = await fee_service.activate(db, fee_id)
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frais non trouvé"
        )
    
    await db.commit()
    return fee


@router.patch("/{fee_id}/deactivate", response_model=FeeResponse)
async def deactivate_fee(
    fee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Désactiver une structure de frais
    
    Requires: Role ADMIN
    """
    fee = await fee_service.deactivate(db, fee_id)
    
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frais non trouvé"
        )
    
    await db.commit()
    return fee


@router.delete("/{fee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fee(
    fee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Supprimer une structure de frais
    
    Requires: Role ADMIN
    """
    deleted = await fee_service.delete(db, fee_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frais non trouvé"
        )
    
    await db.commit()
    return None