import uuid
from typing import List

from fastapi import APIRouter, status, HTTPException, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from watchfiles import awatch

from src.auth.permission import admin_required
from src.db.models import PaymentType
from src.db.session import get_session
from src.schemas.payment_method import PaymentTypeRead, PaymentTypeCreate, PaymentTypeUpdate

router = APIRouter()

async def get_payment_type_or_404(
		id: uuid.UUID,
		session: AsyncSession = Depends(get_session)
):
	stmt = select(PaymentType).where(PaymentType.id == id)
	result = await session.execute(stmt)
	payment_type = result.scalar_one_or_none()
	if not payment_type:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment type does not found")
	return payment_type

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PaymentTypeRead)
async def add_payment_type(payment_type: PaymentTypeCreate, session: AsyncSession = Depends(get_session)):
	payment_type = PaymentType(**payment_type.dict())
	session.add(payment_type)
	await session.commit()
	await session.refresh(payment_type)

	return payment_type


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[PaymentTypeRead])
async def get_all_payment_types(session: AsyncSession = Depends(get_session)):
	stmt = select(PaymentType)
	results = await session.execute(stmt)
	payment_types = results.scalars().all()

	return payment_types

@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=List[PaymentTypeRead])
async def get_payment_type(
		payment_type = Depends(get_payment_type_or_404)
):
	return payment_type


@router.patch("/{id}", response_model=PaymentTypeRead)
async def update_payment_type(
		payment_data: PaymentTypeUpdate,
		payment_type = Depends(get_payment_type_or_404),
		session: AsyncSession = Depends(get_session)
):
	payment_data_dict = payment_data.dict(exclude_unset=True)
	for key, value in payment_data_dict.items():
		setattr(payment_type, key, value)
	session.add(payment_type)
	await session.commit()
	await session.refresh(payment_type)

	return payment_type
import uuid
from typing import List

from fastapi import APIRouter, status, HTTPException, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from watchfiles import awatch

from src.db.models import PaymentType
from src.db.session import get_session
from src.schemas.payment_method import PaymentTypeRead, PaymentTypeCreate, PaymentTypeUpdate

router = APIRouter()

async def get_payment_type_or_404(
		id: uuid.UUID,
		session: AsyncSession = Depends(get_session)
):
	stmt = select(PaymentType).where(PaymentType.id == id)
	result = await session.execute(stmt)
	payment_type = result.scalar_one_or_none()
	if not payment_type:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment type does not found")
	return payment_type

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PaymentTypeRead, dependencies=[Depends(admin_required)])
async def add_payment_type(payment_type: PaymentTypeCreate, session: AsyncSession = Depends(get_session)):
	payment_type = PaymentType(**payment_type.dict())
	session.add(payment_type)
	await session.commit()
	await session.refresh(payment_type)

	return payment_type


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[PaymentTypeRead])
async def get_all_payment_types(session: AsyncSession = Depends(get_session)):
	stmt = select(PaymentType)
	results = await session.execute(stmt)
	payment_types = results.scalars().all()

	return payment_types

@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=List[PaymentTypeRead])
async def get_payment_type(
		payment_type = Depends(get_payment_type_or_404)
):
	return payment_type


@router.patch("/{id}", response_model=PaymentTypeRead, dependencies=[Depends(admin_required)])
async def update_payment_type(
		payment_data: PaymentTypeUpdate,
		payment_type = Depends(get_payment_type_or_404),
		session: AsyncSession = Depends(get_session)
):
	payment_data_dict = payment_data.dict(exclude_unset=True)
	for key, value in payment_data_dict.items():
		setattr(payment_type, key, value)
	session.add(payment_type)
	await session.commit()
	await session.refresh(payment_type)

	return payment_type


@router.delete("/{id}", dependencies=[Depends(admin_required)])
async def delete_payment_type(
		payment_type = Depends(get_payment_type_or_404),
		session: AsyncSession = Depends(get_session)
):
	await session.delete(payment_type)
	await session.commit()
	return {"message": "Type de payment supprimé avec succès"}