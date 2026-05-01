import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.modules.auth.infrastructure.orm.models import UserModel, pwd_context
from app.shared.infrastructure.db import AsyncSessionLocal


DEFAULT_USERS = (
    ("admin@example.com", "123456", "ADMIN"),
    ("owner@example.com", "123456", "MEMBER"),
    ("finder@example.com", "123456", "MEMBER"),
)


async def seed_users():
    async with AsyncSessionLocal() as session:
        for email, password, role in DEFAULT_USERS:
            existing_user = await session.scalar(
                select(UserModel).where(UserModel.email == email).limit(1)
            )

            if existing_user is None:
                user = UserModel(
                    email=email,
                    password_hash=pwd_context.hash(password),
                    role=role,
                    is_active=True,
                )
                session.add(user)
            else:
                user = existing_user
                user.password_hash = pwd_context.hash(password)
                user.role = role
                user.is_active = True

        await session.commit()

        print("Seeded default users:")
        print("  admin@example.com / 123456")
        print("  owner@example.com / 123456")
        print("  finder@example.com / 123456")


if __name__ == "__main__":
    asyncio.run(seed_users())
