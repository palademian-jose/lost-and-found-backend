from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.item_repo import ItemRepository
from ..dtos import ClaimQuestionsDTO, to_claim_questions_dto


@dataclass
class GetItemClaimQuestionsQuery:
    item_id: UUID
    actor_user_id: int


class GetItemClaimQuestionsHandler:
    def __init__(self, item_repo: ItemRepository):
        self.item_repo = item_repo

    async def handle(
        self,
        query: GetItemClaimQuestionsQuery,
    ) -> ClaimQuestionsDTO:
        item = await self.item_repo.get_by_id(query.item_id)

        if item is None:
            raise ValueError("Item not found")

        if item.posted_by_user_id == query.actor_user_id:
            raise ValueError("You cannot claim your own item")

        if item.status.value != "OPEN":
            raise ValueError("Item is not open for claims")

        return to_claim_questions_dto(item)
