from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.item_repo import ItemRepository
from ..dtos import ManagedItemDetailDTO, to_managed_item_detail_dto


@dataclass
class GetItemManagementDetailQuery:
    item_id: UUID
    actor_user_id: int
    is_admin: bool = False


class GetItemManagementDetailHandler:
    def __init__(self, item_repo: ItemRepository):
        self.item_repo = item_repo

    async def handle(
        self,
        query: GetItemManagementDetailQuery,
    ) -> ManagedItemDetailDTO | None:
        item = await self.item_repo.get_by_id(query.item_id)

        if item is None:
            return None

        if not query.is_admin and item.posted_by_user_id != query.actor_user_id:
            raise ValueError("Only the post owner can view private item details")

        return to_managed_item_detail_dto(item)
