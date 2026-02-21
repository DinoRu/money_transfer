import asyncio
import uuid
from datetime import datetime

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import Session as AsyncSessionLocal
from src.db.models import User, UserRole
from src.auth.auth import hash_password


async def seed_users():
    async with AsyncSessionLocal() as session:  # type: AsyncSession

        # Évite les doublons (si seed déjà exécuté)
        result = await session.execute(select(User))
        existing_users = result.scalars().all()

        if existing_users:
            print("⚠️ Users already exist, skipping seed.")
            return

        users = [
            # 🔴 SUPER ADMIN
            User(
                id=uuid.uuid4(),
                full_name="Super Admin",
                email="admin@chapmoney.dev",
                phone="+2250700000000",
                country="CI",
                hash_password=hash_password("Admin@123"),
                role=UserRole.ADMIN,
                profile_picture_url=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),

            # 🇨🇮 USER IVOIRIEN
            User(
                id=uuid.uuid4(),
                full_name="Kouassi Yao",
                email="yao.kouassi@example.ci",
                phone="+2250102030405",
                country="CI",
                hash_password=hash_password("User@123"),
                role=UserRole.USER,
                profile_picture_url=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),

            # 🇸🇳 USER (au choix : Sénégal)
            User(
                id=uuid.uuid4(),
                full_name="Mamadou Ndiaye",
                email="mamadou.ndiaye@example.sn",
                phone="+221770001122",
                country="SN",
                hash_password=hash_password("User@123"),
                role=UserRole.USER,
                profile_picture_url=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        session.add_all(users)
        await session.commit()

        print("✅ Seed users inserted successfully.")


if __name__ == "__main__":
    asyncio.run(seed_users())
