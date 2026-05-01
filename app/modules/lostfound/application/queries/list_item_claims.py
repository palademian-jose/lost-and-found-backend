from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.claim_repo import ClaimRepository
from ...domain.repositories.item_repo import ItemRepository
from ..dtos import ClaimReviewDTO, to_claim_review_dto


@dataclass
class ListItemClaimsQuery:
    item_id: UUID
    actor_user_id: int
    is_admin: bool = False


class ListItemClaimsHandler:
    def __init__(
        self,
        item_repo: ItemRepository,
        claim_repo: ClaimRepository,
    ):
        self.item_repo = item_repo
        self.claim_repo = claim_repo

    async def handle(self, query: ListItemClaimsQuery) -> list[ClaimReviewDTO]:
        item = await self.item_repo.get_by_id(query.item_id)

        if item is None:
            raise ValueError("Item not found")

        if not query.is_admin and item.posted_by_user_id != query.actor_user_id:
            raise ValueError("Only the post owner can view claims")

        claims = await self.claim_repo.list_by_item(query.item_id)
        return [to_claim_review_dto(claim) for claim in claims]
