import uuid
from typing import List

from fastapi import APIRouter, status, HTTPException, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import FCMToken
from src.db.session import get_session
from src.schemas.fcm_token import FCMToken as FCMTokenModel, TokenRequest

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def store_token(token_data: TokenRequest, session: AsyncSession = Depends(get_session)) -> dict:
	new_token = FCMToken(token=token_data.token)
	session.add(new_token)
	await session.commit()
	await session.refresh(new_token)
	return {"message": "Token was stored successful!"}

@router.get("/", status_code=status.HTTP_200_OK, response_model=List[FCMTokenModel])
async def get_tokens(session: AsyncSession = Depends(get_session)):
	stmt = select(FCMToken)
	results = await session.execute(stmt)
	tokens = results.scalars().all()
	return tokens

@router.get('/{pk}', status_code=status.HTTP_200_OK, response_model=FCMTokenModel)
async def get_token(
		pk: uuid.UUID,
		session: AsyncSession = Depends(get_session)
):
	stmt = select(FCMToken).where(FCMToken.pk == pk)
	result = await session.execute(stmt)
	token = result.scalar_one_or_none()
	return token
