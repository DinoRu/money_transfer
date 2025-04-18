from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.auth import decode_token
from src.config import settings
from src.db.models import User
from src.db.session import get_session

security  = HTTPBearer()

async def get_user_or_id(user_id: str, session: AsyncSession = Depends(get_session)):
	stmt = select(User).where(User.id == user_id)
	result = await session.execute(stmt)
	return result.scalar_one_or_none()

async def get_current_user(
		credentials: HTTPAuthorizationCredentials = Security(security),
		session: AsyncSession = Depends(get_session)
):
	token = credentials.credentials
	payload = decode_token(token, settings.SECRET_KEY)
	if not payload:
		raise HTTPException(status_code=401, detail="Invalid token")

	user_id = payload.get("sub")

	user = await get_user_or_id(user_id=user_id, session=session)

	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	return user

