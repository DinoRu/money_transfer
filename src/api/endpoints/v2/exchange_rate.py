"""
Router pour la gestion des taux de change (Exchange Rates)
Endpoints CRUD + conversion de devises (par UUID et par code)
"""
from typing import List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, require_admin, PaginationParams
from src.services import exchange_rate_service, currency_service
from src.schemas.exchange_rate import (
    ExchangeRateCreate, ExchangeRateUpdate, ExchangeRateResponse,
    ExchangeRateWithCurrencies, ExchangeRateConversion, ExchangeRateConversionResponse
)


router = APIRouter(prefix="/exchange-rates", tags=["Exchange Rates"])


@router.get("", response_model=List[ExchangeRateWithCurrencies])
async def list_exchange_rates(
    db: AsyncSession = Depends(get_db),
    pagination: PaginationParams = Depends()
):
    """
    Lister tous les taux de change avec devises
    
    - **skip**: Nombre d'éléments à sauter
    - **limit**: Nombre max d'éléments
    """
    rates = await exchange_rate_service.get_all_with_currencies(db)
    
    # Pagination manuelle
    start = pagination.skip
    end = start + pagination.limit
    
    return rates[start:end]


@router.get("/active", response_model=List[ExchangeRateWithCurrencies])
async def list_active_rates(db: AsyncSession = Depends(get_db)):
    """
    Lister uniquement les taux actifs avec devises
    """
    rates = await exchange_rate_service.get_active(db)
    return rates


@router.get("/currencies/{from_currency_id}/{to_currency_id}", response_model=ExchangeRateWithCurrencies)
async def get_rate_by_currencies(
    from_currency_id: UUID,
    to_currency_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer le taux entre deux devises (par UUID)
    
    - **from_currency_id**: UUID de la devise source
    - **to_currency_id**: UUID de la devise cible
    """
    rate = await exchange_rate_service.get_by_currencies(db, from_currency_id, to_currency_id)
    
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taux de change non trouvé entre ces devises"
        )
    
    return rate


@router.get("/rate/{from_code}/{to_code}", response_model=ExchangeRateWithCurrencies)
async def get_rate_by_codes(
    from_code: str,
    to_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer le taux entre deux devises (par code)
    
    - **from_code**: Code devise source (ex: EUR, RUB, USD)
    - **to_code**: Code devise cible (ex: XOF, XAF, GNF)
    
    Example:
        GET /exchange-rates/rate/EUR/XOF
        
        Returns le taux EUR → XOF avec les détails des devises
    """
    try:
        # Récupérer les devises par code
        from_currency = await currency_service.get_by_code(db, from_code.upper())
        if not from_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Devise {from_code} non trouvée"
            )
        
        to_currency = await currency_service.get_by_code(db, to_code.upper())
        if not to_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Devise {to_code} non trouvée"
            )
        
        # Récupérer le taux
        rate = await exchange_rate_service.get_by_currencies(db, from_currency.id, to_currency.id)
        
        if not rate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Taux de change non trouvé entre {from_code} et {to_code}"
            )
        
        return rate
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/convert", response_model=ExchangeRateConversionResponse)
async def convert_currency(
    conversion: ExchangeRateConversion,
    db: AsyncSession = Depends(get_db)
):
    """
    Convertir un montant d'une devise à une autre (par UUID)
    
    - **from_currency_id**: UUID devise source
    - **to_currency_id**: UUID devise cible
    - **amount**: Montant à convertir
    
    Example:
        ```json
        {
          "from_currency_id": "eur_id",
          "to_currency_id": "xof_id",
          "amount": 100
        }
        ```
    """
    try:
        result = await exchange_rate_service.convert_amount(db, conversion)
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/convert/{from_code}/{to_code}/{amount}", response_model=ExchangeRateConversionResponse)
async def convert_by_currency_codes(
    from_code: str,
    to_code: str,
    amount: float,
    db: AsyncSession = Depends(get_db)
):
    """
    Convertir un montant en utilisant les codes de devise
    
    - **from_code**: Code devise source (ex: EUR, RUB, USD)
    - **to_code**: Code devise cible (ex: XOF, XAF, GNF)
    - **amount**: Montant à convertir
    
    Example:
        GET /exchange-rates/convert/EUR/XOF/100
        
        Returns:
        ```json
        {
          "from_currency": {"code": "EUR", "name": "Euro", "symbol": "€"},
          "to_currency": {"code": "XOF", "name": "Franc CFA", "symbol": "CFA"},
          "rate": 655.0,
          "original_amount": 100,
          "converted_amount": 65500
        }
        ```
    """
    try:
        # Récupérer les devises par code
        from_currency = await currency_service.get_by_code(db, from_code.upper())
        if not from_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Devise {from_code} non trouvée"
            )
        
        to_currency = await currency_service.get_by_code(db, to_code.upper())
        if not to_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Devise {to_code} non trouvée"
            )
        
        # Créer l'objet de conversion
        conversion = ExchangeRateConversion(
            from_currency_id=from_currency.id,
            to_currency_id=to_currency.id,
            amount=Decimal(str(amount))
        )
        
        # Convertir
        result = await exchange_rate_service.convert_amount(db, conversion)
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/calculate-send", response_model=ExchangeRateConversionResponse)
async def calculate_from_send_amount(
    from_code: str,
    to_code: str,
    send_amount: float,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculer le montant à recevoir à partir du montant à envoyer
    
    - **from_code**: Code devise source (ex: EUR)
    - **to_code**: Code devise cible (ex: XOF)
    - **send_amount**: Montant que l'expéditeur envoie
    
    Example:
        ```json
        {
          "from_code": "EUR",
          "to_code": "XOF",
          "send_amount": 100
        }
        ```
        
        Returns:
        ```json
        {
          "from_currency": {"code": "EUR", ...},
          "to_currency": {"code": "XOF", ...},
          "rate": 655.0,
          "original_amount": 100,
          "converted_amount": 65500
        }
        ```
        
        → Le destinataire recevra 65500 XOF
    """
    try:
        # Récupérer les devises
        from_currency = await currency_service.get_by_code(db, from_code.upper())
        if not from_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Devise {from_code} non trouvée"
            )
        
        to_currency = await currency_service.get_by_code(db, to_code.upper())
        if not to_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Devise {to_code} non trouvée"
            )
        
        # Convertir
        conversion = ExchangeRateConversion(
            from_currency_id=from_currency.id,
            to_currency_id=to_currency.id,
            amount=Decimal(str(send_amount))
        )
        
        result = await exchange_rate_service.convert_amount(db, conversion)
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/calculate-receive", response_model=ExchangeRateConversionResponse)
async def calculate_from_receive_amount(
    from_code: str,
    to_code: str,
    receive_amount: float,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculer le montant à envoyer pour que le destinataire reçoive un montant précis
    
    - **from_code**: Code devise source (ex: EUR)
    - **to_code**: Code devise cible (ex: XOF)
    - **receive_amount**: Montant que le destinataire doit recevoir
    
    Example:
        ```json
        {
          "from_code": "EUR",
          "to_code": "XOF",
          "receive_amount": 65500
        }
        ```
        
        Returns:
        ```json
        {
          "from_currency": {"code": "EUR", ...},
          "to_currency": {"code": "XOF", ...},
          "rate": 655.0,
          "original_amount": 100,
          "converted_amount": 65500
        }
        ```
        
        → L'expéditeur doit envoyer 100 EUR
    """
    try:
        # Récupérer les devises
        from_currency = await currency_service.get_by_code(db, from_code.upper())
        if not from_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Devise {from_code} non trouvée"
            )
        
        to_currency = await currency_service.get_by_code(db, to_code.upper())
        if not to_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Devise {to_code} non trouvée"
            )
        
        # Récupérer le taux
        rate_obj = await exchange_rate_service.get_by_currencies(
            db, from_currency.id, to_currency.id
        )
        
        if not rate_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Taux de change non disponible entre {from_code} et {to_code}"
            )
        
        if not rate_obj.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Taux de change inactif"
            )
        
        # Calculer le montant à envoyer (montant_recevoir / taux)
        send_amount = Decimal(str(receive_amount)) / rate_obj.rate
        
        # Créer la réponse
        result = ExchangeRateConversionResponse(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate_obj.rate,
            original_amount=send_amount,
            converted_amount=Decimal(str(receive_amount))
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/stats", response_model=dict)
async def get_exchange_rate_statistics(db: AsyncSession = Depends(get_db)):
    """
    Obtenir les statistiques sur les taux
    """
    total = await exchange_rate_service.count(db)
    active = len(await exchange_rate_service.get_active(db))
    
    return {
        "total_rates": total,
        "active_rates": active,
        "inactive_rates": total - active
    }


@router.get("/{rate_id}", response_model=ExchangeRateWithCurrencies)
async def get_exchange_rate(
    rate_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer un taux par son ID avec devises
    """
    rate = await exchange_rate_service.get_with_currencies(db, rate_id)
    
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taux de change non trouvé"
        )
    
    return rate


@router.post("", response_model=ExchangeRateResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange_rate(
    rate_data: ExchangeRateCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Créer un nouveau taux de change
    
    Requires: Role ADMIN
    """
    try:
        rate = await exchange_rate_service.create(db, rate_data)
        await db.commit()
        return rate
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{rate_id}", response_model=ExchangeRateResponse)
async def update_exchange_rate(
    rate_id: UUID,
    rate_data: ExchangeRateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Mettre à jour un taux de change
    
    Requires: Role ADMIN
    """
    rate = await exchange_rate_service.update(db, rate_id, rate_data)
    
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taux de change non trouvé"
        )
    
    await db.commit()
    return rate


@router.patch("/{rate_id}/activate", response_model=ExchangeRateResponse)
async def activate_rate(
    rate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Activer un taux de change
    
    Requires: Role ADMIN
    """
    rate = await exchange_rate_service.activate(db, rate_id)
    
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taux de change non trouvé"
        )
    
    await db.commit()
    return rate


@router.patch("/{rate_id}/deactivate", response_model=ExchangeRateResponse)
async def deactivate_rate(
    rate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Désactiver un taux de change
    
    Requires: Role ADMIN
    """
    rate = await exchange_rate_service.deactivate(db, rate_id)
    
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taux de change non trouvé"
        )
    
    await db.commit()
    return rate


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exchange_rate(
    rate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Supprimer un taux de change
    
    Requires: Role ADMIN
    """
    deleted = await exchange_rate_service.delete(db, rate_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taux de change non trouvé"
        )
    
    await db.commit()
    return None