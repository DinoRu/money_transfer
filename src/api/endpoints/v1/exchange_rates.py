import uuid
from decimal import Decimal
from typing import List
from datetime import datetime

from fastapi import APIRouter, status, HTTPException, Depends, Response, Query
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.permission import admin_required
from src.db.models import ExchangeRates, Country, Currency
from src.db.session import get_session
from src.schemas.exchange_rate import (
    CreateExchangeRate,
    ExchangeRateListResponse, 
    ExchangeRateRead, 
    UpdateExchangeRate,
    ConversionRequest,
    ConversionResponse,
    ConversionType,
    ExchangeRateQuery,
    ExchangeRateResponse
)

router = APIRouter()


async def get_exchange_rate_or_404(id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    stmt = select(ExchangeRates).where(ExchangeRates.id == id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_required)])
async def create_exchange_rate(
        rate_data: CreateExchangeRate,
        session: AsyncSession = Depends(get_session)
):
    from_currency_result = await session.execute(
        select(Currency).where(Currency.id == rate_data.from_currency_id)
    )
    to_currency_result = await session.execute(
        select(Currency).where(Currency.id == rate_data.to_currency_id)
    )

    from_currency = from_currency_result.scalar_one_or_none()
    to_currency = to_currency_result.scalar_one_or_none()

    if not from_currency:
        raise HTTPException(
            status_code=404,
            detail="Devise source non trouvée!"
        )
    if not to_currency:
        raise HTTPException(
            status_code=404,
            detail="Devise cible non trouvée!"
        )
    
    exchange_rate = ExchangeRates(**rate_data.model_dump())
    session.add(exchange_rate)
    await session.commit()
    await session.refresh(exchange_rate)

    return {"message": "Taux de change ajouté avec succès! 🎉"}


@router.get("", status_code=status.HTTP_200_OK, response_model=List[ExchangeRateRead])
async def get_exchange_rates(session: AsyncSession = Depends(get_session)):
    stmt = select(ExchangeRates).order_by(ExchangeRates.id)
    results = await session.execute(stmt)
    return results.scalars().all()


@router.get("/public" , status_code=status.HTTP_200_OK, response_model=List[ExchangeRateListResponse])
async def get_exchange_rates_public(session: AsyncSession = Depends(get_session)):
    stmt = select(ExchangeRates).options(
        selectinload(ExchangeRates.from_currency),
        selectinload(ExchangeRates.to_currency)
    ).order_by(ExchangeRates.id)
    results = await session.execute(stmt)
    rates = results.scalars().all()
    return [
        ExchangeRateListResponse(
            id=rate.id,
            from_currency=rate.from_currency.code,
            to_currency=rate.to_currency.code,
            rate=float(rate.rate),
        ) for rate in rates
    ]

@router.patch("/{id}", status_code=status.HTTP_200_OK, response_model=ExchangeRateRead, dependencies=[Depends(admin_required)])
async def update_exchange_rate(
        update_rate_data: UpdateExchangeRate,
        exchange_rate: ExchangeRates = Depends(get_exchange_rate_or_404),
        session: AsyncSession = Depends(get_session)
):
    update_rate_data_dict = update_rate_data.model_dump(exclude_unset=True)
    for key, value in update_rate_data_dict.items():
        setattr(exchange_rate, key, value)
    await session.commit()
    await session.refresh(exchange_rate)

    return exchange_rate


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_required)])
async def delete_exchange_rate(
        exchange_rate=Depends(get_exchange_rate_or_404),
        session: AsyncSession = Depends(get_session)
):
    await session.delete(exchange_rate)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# VERSION 1: Endpoint avec POST (recommandé pour Flutter avec body JSON)
@router.post("/convert", status_code=status.HTTP_200_OK, response_model=ConversionResponse)
async def convert_currency_post(
        conversion_data: ConversionRequest,
        session: AsyncSession = Depends(get_session)
):
    """
    Convertit un montant entre deux devises.
    
    Vous pouvez spécifier soit:
    - send_amount: le montant que vous voulez envoyer
    - receive_amount: le montant que vous voulez recevoir
    
    Exemple pour Flutter:
    ```dart
    final response = await http.post(
        Uri.parse('$baseUrl/convert'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
            'from_currency': 'USD',
            'to_currency': 'EUR',
            'send_amount': 100.0
        })
    );
    ```
    """
    from_currency_upper = conversion_data.from_currency
    to_currency_upper = conversion_data.to_currency

    # Vérifier que les devises existent
    from_currency_db = await _get_currency_by_code(session, from_currency_upper)
    to_currency_db = await _get_currency_by_code(session, to_currency_upper)

    # Récupérer le taux de change
    exchange_rate = await _get_exchange_rate(
        session, 
        from_currency_db.id, 
        to_currency_db.id,
        from_currency_upper,
        to_currency_upper
    )

    # Calculer les montants selon le type de conversion
    if conversion_data.send_amount is not None:
        # L'utilisateur spécifie le montant à envoyer
        send_amount = conversion_data.send_amount
        receive_amount = send_amount * exchange_rate.rate
        conversion_type = ConversionType.SEND
    else:
        # L'utilisateur spécifie le montant à recevoir
        receive_amount = conversion_data.receive_amount
        send_amount = receive_amount / exchange_rate.rate
        conversion_type = ConversionType.RECEIVE

    return ConversionResponse(
        from_currency=from_currency_upper,
        to_currency=to_currency_upper,
        send_amount=send_amount,
        receive_amount=receive_amount,
        exchange_rate=exchange_rate.rate,
        conversion_type=conversion_type,
        timestamp=datetime.utcnow()
    )


# VERSION 2: Endpoint avec GET (pour compatibilité)
@router.get("/convert", status_code=status.HTTP_200_OK, response_model=ConversionResponse)
async def convert_currency_get(
        from_currency: str = Query(..., description="Code de la devise source (ex: USD)"),
        to_currency: str = Query(..., description="Code de la devise cible (ex: EUR)"),
        send_amount: Decimal = Query(None, description="Montant à envoyer", gt=0),
        receive_amount: Decimal = Query(None, description="Montant à recevoir", gt=0),
        session: AsyncSession = Depends(get_session)
):
    """
    Version GET de l'endpoint de conversion.
    
    Exemple pour Flutter:
    ```dart
    final queryParams = {
        'from_currency': 'USD',
        'to_currency': 'EUR',
        'send_amount': '100.0'
    };
    final uri = Uri.parse('$baseUrl/convert').replace(queryParameters: queryParams);
    final response = await http.get(uri);
    ```
    """
    # Validation manuelle car c'est un GET avec query params
    if send_amount is None and receive_amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous devez fournir soit 'send_amount' soit 'receive_amount'"
        )
    
    if send_amount is not None and receive_amount is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez fournir qu'un seul montant"
        )

    # Créer un objet ConversionRequest pour réutiliser la logique
    conversion_data = ConversionRequest(
        from_currency=from_currency,
        to_currency=to_currency,
        send_amount=send_amount,
        receive_amount=receive_amount
    )

    # Réutiliser la logique du POST
    return await convert_currency_post(conversion_data, session)


# Endpoint bonus: Obtenir juste le taux de change
@router.get("/rate", status_code=status.HTTP_200_OK, response_model=ExchangeRateResponse)
async def get_exchange_rate_info(
        from_currency: str = Query(..., description="Code de la devise source"),
        to_currency: str = Query(..., description="Code de la devise cible"),
        session: AsyncSession = Depends(get_session)
):
    """
    Récupère le taux de change actuel entre deux devises sans faire de conversion.
    Utile pour afficher le taux dans l'interface Flutter.
    
    Exemple Flutter:
    ```dart
    final uri = Uri.parse('$baseUrl/rate').replace(queryParameters: {
        'from_currency': 'USD',
        'to_currency': 'EUR'
    });
    final response = await http.get(uri);
    ```
    """
    from_currency_upper = from_currency.upper()
    to_currency_upper = to_currency.upper()

    from_currency_db = await _get_currency_by_code(session, from_currency_upper)
    to_currency_db = await _get_currency_by_code(session, to_currency_upper)

    exchange_rate = await _get_exchange_rate(
        session,
        from_currency_db.id,
        to_currency_db.id,
        from_currency_upper,
        to_currency_upper
    )

    return ExchangeRateResponse(
        from_currency=from_currency_upper,
        to_currency=to_currency_upper,
        rate=exchange_rate.rate,
        inverse_rate=Decimal(1) / exchange_rate.rate,
        last_updated=exchange_rate.updated_at if hasattr(exchange_rate, 'updated_at') else None
    )


# Fonctions utilitaires
async def _get_currency_by_code(session: AsyncSession, currency_code: str) -> Currency:
    """Récupère une devise par son code ou lève une exception"""
    result = await session.execute(
        select(Currency).where(Currency.code == currency_code)
    )
    currency = result.scalar_one_or_none()
    
    if not currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La devise '{currency_code}' n'existe pas"
        )
    
    return currency


async def _get_exchange_rate(
    session: AsyncSession,
    from_currency_id: str,
    to_currency_id: str,
    from_code: str,
    to_code: str
) -> ExchangeRates:
    """Récupère le taux de change ou lève une exception"""
    result = await session.execute(
        select(ExchangeRates).where(
            ExchangeRates.from_currency_id == from_currency_id,
            ExchangeRates.to_currency_id == to_currency_id
        )
    )
    exchange_rate = result.scalar_one_or_none()
    
    if not exchange_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun taux de change trouvé de {from_code} vers {to_code}"
        )
    
    return exchange_rate