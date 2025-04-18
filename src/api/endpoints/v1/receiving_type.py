import uuid
from typing import List
from fastapi import APIRouter, status, HTTPException
from fastapi.params import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.permission import admin_required
from src.db.models import ReceivingType
from src.db.session import get_session
from src.schemas.rtype import ReceivingTypeRead, ReceivingTypeCreate, ReceivingTypeUpdate

router = APIRouter()

async def get_receiving_type_or_404(id: uuid.UUID, session: AsyncSession = Depends(get_session)):
	stmt = select(ReceivingType).where(ReceivingType.id == id)
	result = await session.execute(stmt)
	receiving_type = result.scalar_one_or_none()
	if not receiving_type:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type dont found")
	return receiving_type

@router.post("/type", status_code=status.HTTP_201_CREATED, response_model=ReceivingTypeRead, dependencies=[Depends(admin_required)])
async def type_create(
		data: ReceivingTypeCreate,
		session: AsyncSession = Depends(get_session)
):
	type = ReceivingType(**data.dict())
	session.add(type)
	await session.commit()
	await session.refresh(type)
	return type

@router.get("/", status_code=status.HTTP_200_OK, response_model=List[ReceivingTypeRead])
async def get_receiving_types(session: AsyncSession = Depends(get_session)):
	stmt = select(ReceivingType)
	results = await session.execute(stmt)
	receiving_types = results.scalars().all()
	return receiving_types


@router.get("/{id}", response_model=ReceivingTypeRead, status_code=status.HTTP_200_OK)
async def receiving_type(
		receiving_type = Depends(get_receiving_type_or_404),
		session: AsyncSession = Depends(get_session)
):
	return receiving_type

@router.patch("/update/{id}", status_code=status.HTTP_200_OK, response_model=ReceivingTypeRead, dependencies=[Depends(admin_required)])
async def update_type(
		receiving_type_data: ReceivingTypeUpdate,
		receiving_type = Depends(get_receiving_type_or_404),
		session: AsyncSession = Depends(get_session)
):
	receiving_type_data_dict = receiving_type_data.dict(exclude_unset=True)
	for key, value in receiving_type_data_dict.items():
		setattr(receiving_type, key, value)
	session.add(receiving_type)
	await session.commit()
	await session.refresh(receiving_type)
	return receiving_type


@router.delete("/{id}", dependencies=[Depends(admin_required)])
async def delete_receiving_type(
		type_receiving = Depends(get_receiving_type_or_404),
		session: AsyncSession = Depends(get_session)
) -> dict:
	await session.delete(type_receiving)
	await session.commit()
	return {"message": "Type de réception supprimé avec succès"}