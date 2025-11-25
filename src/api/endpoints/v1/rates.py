from decimal import localcontext, Decimal
from typing import Dict, Any

from fastapi import APIRouter, status, Path
from fastapi.params import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select

# from src.db.models import Rate
from src.db.session import get_session
from src.schemas.rates import RateRequest, Rates, ConvertResponseModel

router = APIRouter()


async def get_rates(session: AsyncSession = Depends(get_session)):
	stmt = select(Rate).order_by(Rate.currency)
	result = await session.execute(stmt)
	rates = result.scalars().all()
	return {rate.currency: rate.rate for rate in rates}

async def get_rate(
		base: str,
		to: str,
		rates: Dict[str, Any] = Depends(get_rates)
) -> Rates:
	with localcontext() as ctx:
		ctx.prec = 2 * 6
		rate = rates[to] / rates[base]
	rate = round(rate, 6)
	return Rates(quote=rate)


async def convert(amount: Decimal, rate: Rates = Depends(get_rate)):
	with localcontext() as ctx:
		ctx.prec = 2
		result = rate.quote * amount
	return round(result, 2)


@router.post("/rate", status_code=status.HTTP_200_OK)
async def add_rate(data: RateRequest, session: AsyncSession = Depends(get_session)):
	for currency, rate in data.conversion_rates.items():
		query = select(Rate).where(Rate.currency == currency)
		result = await session.execute(query)
		existing_rate = result.scalar_one_or_none()
		if existing_rate:
			existing_rate.rate = rate
		else:
			rates = Rate(currency=currency, rate=rate)
			session.add(rates)
	await session.commit()
	return {"message": "Rate successfully added ☺️"}


@router.get("/rates", status_code=status.HTTP_200_OK)
async def get_rates(session: AsyncSession = Depends(get_session)):
	stmt = select(Rate).order_by(Rate.currency)
	result = await session.execute(stmt)
	rates = result.scalars().all()
	return {
		"response": "Success",
		"base_code": "USD",
		"conversion_rates": {rate.currency: Decimal(rate.rate) for rate in rates}
	}


@router.get("/{base}/{to}/{amount}", status_code=status.HTTP_200_OK)
async def convert_amount(
		base: str = Path(...,
						 title="Base currency",
						 description="Base currency for conversion",
						 ),
		to: str = Path(...,
								 title="Target currency",
								 description="Target currency for conversion",
								 ),
		amount: Decimal = Path(
			...,
			gt=0,
			title="Amount of money",
			description="Amount of money to be converted"
		),
		rate: Rates = Depends(get_rate),
		result: Decimal = Depends(convert)
) -> Dict[str, Any]:
	return {
		"base": base,
		"to": to,
		"amount": amount,
		"rates": rate,
		"result": result
	}