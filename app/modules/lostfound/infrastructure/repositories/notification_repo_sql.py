from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...application.dtos import to_notification_dto
from ..orm.models import NotificationModel


class NotificationRepositorySQL:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        *,
        user_id: int,
        type: str,
        title: str,
        body: str,
        related_item_id: str | None = None,
        related_claim_id: str | None = None,
    ):
        self.session.add(
            NotificationModel(
                user_id=user_id,
                type=type,
                title=title,
                body=body,
                related_item_id=related_item_id,
                related_claim_id=related_claim_id,
            )
        )
        await self.session.flush()

    async def list_for_user(self, user_id: int):
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
        )
        result = await self.session.execute(stmt)
        return [to_notification_dto(model) for model in result.scalars().all()]

    async def mark_all_read(self, user_id: int):
        stmt = select(NotificationModel).where(NotificationModel.user_id == user_id)
        result = await self.session.execute(stmt)

        for notification in result.scalars().all():
            notification.is_read = True

        await self.session.flush()
