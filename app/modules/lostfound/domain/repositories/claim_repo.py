from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from ..entities.claim import Claim


class ClaimRepository(ABC):
    @abstractmethod
    async def get_by_id(self, claim_id: UUID) -> Optional[Claim]:
        pass

    @abstractmethod
    async def get_by_id_for_update(self, claim_id: UUID) -> Optional[Claim]:
        pass

    @abstractmethod
    async def create(
        self,
        claim_id: UUID,
        item_id: UUID,
        claimant_user_id: int,
        answers: List[str],
        proof_statement: str | None,
        submitted_at: datetime,
    ) -> None:
        pass

    @abstractmethod
    async def save(self, claim: Claim) -> None:
        pass

    @abstractmethod
    async def list_by_item(self, item_id: UUID) -> list[Claim]:
        pass

    @abstractmethod
    async def list_by_claimant(self, claimant_user_id: int) -> list[Claim]:
        pass
