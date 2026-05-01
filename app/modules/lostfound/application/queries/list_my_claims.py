from dataclasses import dataclass

from ...domain.repositories.claim_repo import ClaimRepository
from ..dtos import ClaimReviewDTO, to_claim_review_dto


@dataclass
class ListMyClaimsQuery:
    claimant_user_id: int


class ListMyClaimsHandler:
    def __init__(self, claim_repo: ClaimRepository):
        self.claim_repo = claim_repo

    async def handle(self, query: ListMyClaimsQuery) -> list[ClaimReviewDTO]:
        claims = await self.claim_repo.list_by_claimant(query.claimant_user_id)
        return [to_claim_review_dto(claim) for claim in claims]
