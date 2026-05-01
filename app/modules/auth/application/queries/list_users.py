from dataclasses import dataclass

from app.modules.auth.domain.user_role import UserRole

from ..dtos import UserSummaryDTO, to_user_summary_dto


@dataclass
class ListUsersQuery:
    role: UserRole | None = None
    is_active: bool | None = None
    limit: int = 100
    offset: int = 0


class ListUsersHandler:
    def __init__(self, user_repo):
        self.user_repo = user_repo

    async def handle(self, query: ListUsersQuery) -> list[UserSummaryDTO]:
        users = await self.user_repo.list(
            role=query.role.value if query.role else None,
            is_active=query.is_active,
            limit=query.limit,
            offset=query.offset,
        )
        return [to_user_summary_dto(user) for user in users]
