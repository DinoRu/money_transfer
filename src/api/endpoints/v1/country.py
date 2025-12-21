# from typing import List

# from fastapi import APIRouter, status, Depends, HTTPException, Response
# from sqlalchemy.orm import joinedload, selectinload
# from sqlmodel import select
# from sqlmodel.ext.asyncio.session import AsyncSession

# from src.auth.permission import admin_required
# from src.db.models import Country, Currency
# from src.db.session import get_db
# from src.schemas.currency import CountryModel, CountryCreate, UpdateCountrySchema

# router = APIRouter()

# async def get_country_or_404(
# 		country_id: str,
# 		session: AsyncSession = Depends(get_db)
# ):
# 	stmt = select(Country).where(Country.id == country_id)
# 	result = await session.execute(stmt)
# 	country = result.scalar_one_or_none()
# 	if not country:
# 		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country does not found")
# 	return country


# @router.get("/", status_code=status.HTTP_200_OK, response_model=List[CountryModel])
# async def get_all_countries(
# 		session: AsyncSession = Depends(get_db)
# ):
# 	stmt = select(Country).options(
# 		selectinload(Country.currency),
# 		selectinload(Country.payment_types),
# 		selectinload(Country.receiving_types)
# 	)
# 	result = await session.execute(stmt)
# 	return result.scalars().all()


# @router.post("/", status_code=status.HTTP_201_CREATED, response_model=CountryModel, dependencies=[Depends(admin_required)])
# async def add_country(
# 		country_data: CountryCreate,
# 		session: AsyncSession = Depends(get_db)
# ):
# 	country_result = await session.execute(select(Country).where(Country.code_iso == country_data.code_iso))
# 	country = country_result.scalar_one_or_none()
# 	if country:
# 		raise HTTPException(
# 			status_code=400,
# 			detail="Country with this ISO code already exists"
# 		)
# 	currency_result = await session.execute(select(Currency).where(Currency.id == country_data.currency_id))
# 	currency = currency_result.scalar_one_or_none()
# 	if not currency:
# 		raise HTTPException(status_code=404, detail="Currency not found")
# 	country = Country(**country_data.dict())
# 	session.add(country)
# 	await session.commit()
# 	await session.refresh(country)


# 	stmt = select(Country).options(
# 		selectinload(Country.currency),
# 		selectinload(Country.payment_types),
# 		selectinload(Country.receiving_types)
# 	).where(Country.id == country.id)

# 	result = await session.execute(stmt)
# 	country_with_relations = result.scalar_one()
# 	return country_with_relations


# @router.patch("/{country_id}", response_model=CountryModel, dependencies=[Depends(admin_required)])
# async def update_country(
# 		county_update: UpdateCountrySchema,
# 		country: Country = Depends(get_country_or_404),
# 		session: AsyncSession = Depends(get_db)
# ):
# 	country_data_dict = county_update.dict(exclude_unset=True)
# 	for key, value in country_data_dict.items():
# 		setattr(country, key, value)

# 	session.add(country)
# 	await session.commit()
# 	await session.refresh(country)
# 	return country


# @router.delete("/{country_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_required)])
# async def delete_country(
# 		country = Depends(get_country_or_404),
# 		session: AsyncSession = Depends(get_db)
# ):
# 	await session.delete(country)
# 	await session.commit()
# 	return Response(status_code=status.HTTP_204_NO_CONTENT)

