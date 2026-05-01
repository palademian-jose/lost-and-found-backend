from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...application.dtos import to_audit_log_dto
from ..orm.models import AuditLogModel


class AuditLogRepositorySQL:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        actor_user_id: int,
        action: str,
        target_type: str,
        target_id: str,
    ):
        self.session.add(
            AuditLogModel(
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
            )
        )
        await self.session.flush()

    async def list(
        self,
        *,
        actor_user_id: int | None = None,
        action: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        stmt = select(AuditLogModel).order_by(
            AuditLogModel.created_at.desc(),
            AuditLogModel.id.desc(),
        )

        if actor_user_id is not None:
            stmt = stmt.where(AuditLogModel.actor_user_id == actor_user_id)

        if action:
            stmt = stmt.where(AuditLogModel.action == action)

        if target_type:
            stmt = stmt.where(AuditLogModel.target_type == target_type)

        if target_id:
            stmt = stmt.where(AuditLogModel.target_id == target_id)

        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [to_audit_log_dto(model) for model in models]
