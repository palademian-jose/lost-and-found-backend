from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.item_repo import ItemRepository
from ..dtos import ItemDetailDTO, to_item_detail_dto


@dataclass
class GetItemDetailQuery:
    item_id: UUID


class GetItemDetailHandler:
    def __init__(self, item_repo: ItemRepository):
        self.item_repo = item_repo

    async def handle(self, query: GetItemDetailQuery) -> ItemDetailDTO | None:
        item = await self.item_repo.get_by_id(query.item_id)

        if item is None:
            return None

        return to_item_detail_dto(item)
