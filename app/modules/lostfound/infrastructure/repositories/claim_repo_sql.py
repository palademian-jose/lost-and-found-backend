from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...domain.entities.claim import Claim
from ...domain.repositories.claim_repo import ClaimRepository
from ...domain.value_objects.claim_status import ClaimStatus
from ..orm.mappers import map_claim_model_to_domain
from ..orm.models import ClaimAnswerModel, ClaimModel


class ClaimRepositorySQL(ClaimRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, claim_id: UUID):
        stmt = (
            select(ClaimModel)
            .options(selectinload(ClaimModel.answers))
            .where(ClaimModel.id == str(claim_id))
        )

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return map_claim_model_to_domain(model)

    async def get_by_id_for_update(self, claim_id: UUID):
        stmt = (
            select(ClaimModel)
            .options(selectinload(ClaimModel.answers))
            .where(ClaimModel.id == str(claim_id))
            .with_for_update()
        )

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return map_claim_model_to_domain(model)

    async def create(
        self,
        claim_id: UUID,
        item_id: UUID,
        claimant_user_id: int,
        answers: List[str],
        proof_statement: str | None,
        submitted_at: datetime,
    ) -> None:
        model = ClaimModel(
            id=str(claim_id),
            item_id=str(item_id),
            claimant_user_id=claimant_user_id,
            proof_statement=proof_statement,
            status=ClaimStatus.SUBMITTED.value,
            submitted_at=submitted_at,
        )

        for answer in answers:
            model.answers.append(ClaimAnswerModel(answer=answer))

        self.session.add(model)
        await self.session.flush()

    async def save(self, claim: Claim) -> None:
        model = await self.session.get(ClaimModel, str(claim.id))

        if not model:
            raise ValueError("Claim not found")

        model.status = claim.status.value
        model.decision_reason = claim.decision_reason
        model.decided_at = claim.decided_at
        await self.session.flush()

    async def list_by_item(self, item_id: UUID) -> list[Claim]:
        stmt = (
            select(ClaimModel)
            .options(selectinload(ClaimModel.answers))
            .where(ClaimModel.item_id == str(item_id))
            .order_by(ClaimModel.submitted_at.desc())
        )

        result = await self.session.execute(stmt)
        models = result.scalars().unique().all()
        return [map_claim_model_to_domain(model) for model in models]

    async def list_by_claimant(self, claimant_user_id: int) -> list[Claim]:
        stmt = (
            select(ClaimModel)
            .options(selectinload(ClaimModel.answers))
            .where(ClaimModel.claimant_user_id == claimant_user_id)
            .order_by(ClaimModel.submitted_at.desc())
        )

        result = await self.session.execute(stmt)
        models = result.scalars().unique().all()
        return [map_claim_model_to_domain(model) for model in models]
