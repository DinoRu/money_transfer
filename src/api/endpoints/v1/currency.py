import uuid
from typing import List

from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_utils import Currency as CurrencyType
from sqlmodel import select

from src.auth.permission import admin_required
from src.db.models import Currency
from src.db.session import get_session
from src.schemas.currency import CurrencyModel, CurrencyCreate

router = APIRouter()

async def get_or_404_currency(id: uuid.UUID, session: AsyncSession = Depends(get_session)):
	stmt = select(Currency).where(Currency.id == id)
	result = await session.execute(stmt)
	currency = result.scalar_one_or_none()
	return currency

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CurrencyModel, dependencies=[Depends(admin_required)])
async def create_currency(
		currency_schema: CurrencyCreate,
		session: AsyncSession = Depends(get_session)
):
	currency_type = CurrencyType(currency_schema.code)
	currency_code = currency_type.code
	currency_name = currency_type.name
	currency_symbol = currency_type.symbol

	currency = Currency(
		code=currency_code,
		name=currency_name,
		symbol=currency_symbol
	)

	session.add(currency)
	await session.commit()
	return currency


@router.get("/currencies", response_model=List[Currency], status_code=status.HTTP_200_OK)
async def get_all_currencies(
		session: AsyncSession = Depends(get_session)
):
	stmt = select(Currency)
	result = await session.execute(stmt)
	return result.scalars().all()


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_currency(
		currency: Currency = Depends(get_or_404_currency),
		session: AsyncSession = Depends(get_session)
):
	await session.delete(currency)
	await session.commit()
	return {'message': "Devise supprimé avec succès"}


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_currency(
		session: AsyncSession = Depends(get_session)
):
	stmt = select(Currency)
	await session.delete(stmt)
	await session.commit()
	return {'message': 'Toutes les devise ont été supprimé!'}