from dataclasses import dataclass

from ..dtos import AuditLogDTO


@dataclass
class ListAuditLogsQuery:
    actor_user_id: int | None = None
    action: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    limit: int = 100
    offset: int = 0


class ListAuditLogsHandler:
    def __init__(self, audit_repo):
        self.audit_repo = audit_repo

    async def handle(self, query: ListAuditLogsQuery) -> list[AuditLogDTO]:
        return await self.audit_repo.list(
            actor_user_id=query.actor_user_id,
            action=query.action,
            target_type=query.target_type,
            target_id=query.target_id,
            limit=query.limit,
            offset=query.offset,
        )
