from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.config import settings

engine = AsyncEngine(create_engine(url=settings.active_database_url()))
Session = async_sessionmaker(
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False
)

async def get_session() -> AsyncGenerator:
	async with Session() as session:
		yield session
