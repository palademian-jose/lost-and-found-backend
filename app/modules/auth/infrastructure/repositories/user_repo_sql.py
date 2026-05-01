from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.modules.auth.infrastructure.orm.models import UserModel


class UserRepository:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_email(self, email: str) -> UserModel | None:

        stmt = (
            select(UserModel)
            .where(UserModel.email == email)
            .limit(1)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


    async def get_by_id(self, user_id: int) -> UserModel | None:

        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .limit(1)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: str,
    ) -> UserModel:
        user = UserModel(
            email=email,
            password_hash=password_hash,
            role=role,
        )

        self._session.add(user)
        await self._session.flush()
        return user

    async def list(
        self,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserModel]:
        stmt = select(UserModel).order_by(UserModel.created_at.desc(), UserModel.id.desc())

        if role:
            stmt = stmt.where(UserModel.role == role)

        if is_active is not None:
            stmt = stmt.where(UserModel.is_active == is_active)

        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def set_active_status(
        self,
        *,
        user_id: int,
        is_active: bool,
    ) -> UserModel | None:
        user = await self.get_by_id(user_id)

        if user is None:
            return None

        user.is_active = is_active
        await self._session.flush()
        return user

    async def set_role(
        self,
        *,
        user_id: int,
        role: str,
    ) -> UserModel | None:
        user = await self.get_by_id(user_id)

        if user is None:
            return None

        user.role = role
        await self._session.flush()
        return user

    async def count_active_admins(self) -> int:
        stmt = select(func.count()).select_from(UserModel).where(
            UserModel.role == "ADMIN",
            UserModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
