from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.application.dtos import to_user_profile_dto
from app.modules.auth.infrastructure.orm.models import UserProfileModel


class UserProfileRepositorySQL:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, user_id: int):
        profile = await self.session.get(UserProfileModel, user_id)

        if profile is None:
            profile = UserProfileModel(user_id=user_id)
            self.session.add(profile)
            await self.session.flush()

        return profile

    async def get_dto(self, user_id: int):
        profile = await self.get_or_create(user_id)
        return to_user_profile_dto(profile)

    async def update(
        self,
        *,
        user_id: int,
        full_name: str | None,
        phone: str | None,
        department: str | None,
        preferred_contact_method: str | None,
    ):
        profile = await self.get_or_create(user_id)
        profile.full_name = full_name
        profile.phone = phone
        profile.department = department
        profile.preferred_contact_method = preferred_contact_method
        await self.session.flush()
        return to_user_profile_dto(profile)
