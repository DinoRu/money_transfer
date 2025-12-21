# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from uuid import UUID
# from typing import List

# from src.auth.permission import admin_required
# from src.db.models import Fee
# from src.db.session import get_db
# from src.schemas.fees import FeeView, CreateFee, UpdateFee

# router = APIRouter()


# @router.post("/", response_model=FeeView, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_required)])
# async def create_fee(fee_data: CreateFee, session: AsyncSession = Depends(get_db)):
# 	query = select(Fee).where(
# 		Fee.from_country_id == str(fee_data.from_country_id),
# 		Fee.to_country_id == str(fee_data.to_country_id)
# 	)
# 	result = await session.execute(query)
# 	existing_fee = result.scalars().first()

# 	if existing_fee:
# 		raise HTTPException(
# 			status_code=400,
# 			detail="Fee already exists for this from_country_id and to_country_id"
# 		)

# 	fee = Fee(**fee_data.dict())
# 	session.add(fee)
# 	await session.commit()
# 	await session.refresh(fee)
# 	return fee


# @router.get("/", response_model=List[FeeView])
# async def get_all_fees(session: AsyncSession = Depends(get_db)):
# 	result = await session.execute(select(Fee))
# 	fees = result.scalars().all()
# 	return fees



# @router.get("/by-countries", response_model=List[FeeView])
# async def get_fee_by_countries(
# 		from_country_id: UUID,
# 		to_country_id: UUID,
# 		session: AsyncSession = Depends(get_db)
# ):
# 	result = await session.execute(
# 		select(Fee)
# 		.where(
# 			Fee.from_country_id == from_country_id,
# 			Fee.to_country_id == to_country_id
# 		)
# 	)
# 	fees = result.scalars().all()

# 	if not fees:
# 		raise HTTPException(
# 			status_code=404,
# 			detail="Aucun frais trouvé pour cette paire de pays"
# 		)

# 	return fees




# @router.get("/{id}", response_model=FeeView)
# async def get_fee(id: UUID, session: AsyncSession = Depends(get_db)):
# 	result = await session.execute(select(Fee).where(Fee.id == id))
# 	fee = result.scalars().first()
# 	if not fee:
# 		raise HTTPException(status_code=404, detail="Fee not found")
# 	return fee


# @router.put("/{id}", response_model=FeeView, dependencies=[Depends(admin_required)])
# async def update_fee(id: UUID, fee_data: UpdateFee, session: AsyncSession = Depends(get_db)):
# 	result = await session.execute(select(Fee).where(Fee.id == id))
# 	fee = result.scalars().first()
# 	if not fee:
# 		raise HTTPException(status_code=404, detail="Fee not found")

# 	fee.fee = fee_data.fee
# 	await session.commit()
# 	await session.refresh(fee)
# 	return fee


# @router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_required)])
# async def delete_fee(id: UUID, session: AsyncSession = Depends(get_db)):
# 	result = await session.execute(select(Fee).where(Fee.id == id))
# 	fee = result.scalars().first()
# 	if not fee:
# 		raise HTTPException(status_code=404, detail="Fee not found")

# 	await session.delete(fee)
# 	await session.commit()
