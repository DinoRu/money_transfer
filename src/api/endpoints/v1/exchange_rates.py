import uuid
from decimal import Decimal
from typing import List

from fastapi import APIRouter, status, HTTPException, Depends, Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.permission import admin_required
from src.db.models import ExchangeRates, Country, Currency
from src.db.session import get_session
from src.schemas.rates import CreateExchangeRate, ExchangeRateRead, UpdateExchangeRate

router = APIRouter()

async def get_exchange_rate_or_404(id: uuid.UUID, session: AsyncSession = Depends(get_session)):
	stmt = select(ExchangeRates).where(ExchangeRates.id == id)
	result = await session.execute(stmt)
	return result.scalar_one_or_none()

@router.post("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_required)])
async def create_exchange_rate(
		rate_data: CreateExchangeRate,
		session: AsyncSession = Depends(get_session)
):
	from_country_result = await session.execute(select(Currency).where(Currency.id == rate_data.from_currency_id))
	to_country_result = await session.execute(select(Currency).where(Currency.id == rate_data.to_currency_id))

	from_currency = from_country_result.scalar_one_or_none()
	to_currency = to_country_result.scalar_one_or_none()

	if not from_currency:
		raise HTTPException(
			status_code=404,
			detail="Base country not found!"
		)
	if not to_currency:
		raise HTTPException(
			status_code=404,
			detail="Target country not found!"
		)
	exchange_rate = ExchangeRates(**rate_data.dict())
	session.add(exchange_rate)
	await session.commit()
	await session.refresh(exchange_rate)

	return {"message": "Exchange was successfully added! 🎉"}


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[ExchangeRateRead])
async def get_exchange_rates(session: AsyncSession = Depends(get_session)):
	stmt = select(ExchangeRates).order_by(ExchangeRates.id)
	results = await session.execute(stmt)
	return results.scalars().all()


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


@router.get("/convert", status_code=status.HTTP_200_OK)
async def convert_currency(
		from_currency: str,
		to_currency: str,
		amount: Decimal,
		session: AsyncSession = Depends(get_session)
):
	if amount <= 0:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Amount must be a positive number."
		)

	from_currency_upper = from_currency.upper()
	to_currency_upper = to_currency.upper()

	# Check if from_currency exists
	from_currency_result = await session.execute(
		select(Currency).where(Currency.code == from_currency_upper)
	)
	from_currency_db = from_currency_result.scalar_one_or_none()
	if not from_currency_db:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Currency with code {from_currency_upper} not found."
		)

	# Check if to_currency exists
	to_currency_result = await session.execute(
		select(Currency).where(Currency.code == to_currency_upper)
	)
	to_currency_db = to_currency_result.scalar_one_or_none()
	if not to_currency_db:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Currency with code {to_currency_upper} not found."
		)

	# Check exchange rate
	exchange_rate_result = await session.execute(
		select(ExchangeRates).where(
			ExchangeRates.from_currency_id == from_currency_db.id,
			ExchangeRates.to_currency_id == to_currency_db.id
		)
	)
	exchange_rate = exchange_rate_result.scalar_one_or_none()
	if not exchange_rate:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"No exchange rate found from {from_currency_upper} to {to_currency_upper}."
		)

	converted_amount = amount * exchange_rate.rate

	return {
		"from_currency": from_currency_upper,
		"to_currency": to_currency_upper,
		"original_amount": amount,
		"converted_amount": converted_amount,
		"rate": exchange_rate.rate
	}