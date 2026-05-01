from dataclasses import dataclass
from datetime import UTC, datetime
from typing import List
from uuid import UUID, uuid4

from ...domain.entities.item import ItemTimelineEvent
from ...domain.repositories.claim_repo import ClaimRepository
from ...domain.repositories.item_repo import ItemRepository


@dataclass
class SubmitClaimCommand:
    item_id: UUID
    claimant_user_id: int
    answers: List[str]
    proof_statement: str | None


class SubmitClaimHandler:
    def __init__(
        self,
        item_repo: ItemRepository,
        claim_repo: ClaimRepository,
        audit_repo=None,
        notification_repo=None,
    ):
        self.item_repo = item_repo
        self.claim_repo = claim_repo
        self.audit_repo = audit_repo
        self.notification_repo = notification_repo

    async def handle(self, cmd: SubmitClaimCommand) -> UUID:
        item = await self.item_repo.get_by_id_for_update(cmd.item_id)

        if not item:
            raise ValueError("Item not found")

        if item.posted_by_user_id == cmd.claimant_user_id:
            raise ValueError("You cannot claim your own item")

        if item.status.value != "OPEN":
            raise ValueError("Item is not open for claims")

        if len(cmd.answers) != len(item.verification_questions):
            raise ValueError("Answers count mismatch")

        claim_id = uuid4()

        await self.claim_repo.create(
            claim_id=claim_id,
            item_id=item.id,
            claimant_user_id=cmd.claimant_user_id,
            answers=cmd.answers,
            proof_statement=cmd.proof_statement,
            submitted_at=datetime.now(UTC).replace(tzinfo=None),
        )

        item.mark_pending(claim_id)
        event_time = datetime.now(UTC).replace(tzinfo=None)
        item.timeline.append(
            ItemTimelineEvent(
                event_type="CLAIM_SUBMITTED",
                description="A claim was submitted and is awaiting review.",
                actor_user_id=cmd.claimant_user_id,
                created_at=event_time,
            )
        )
        await self.item_repo.save(item)

        if self.audit_repo is not None:
            await self.audit_repo.add(
                actor_user_id=cmd.claimant_user_id,
                action="CLAIM_SUBMITTED",
                target_type="claim",
                target_id=str(claim_id),
            )

        if self.notification_repo is not None:
            await self.notification_repo.add(
                user_id=item.posted_by_user_id,
                type="CLAIM_SUBMITTED",
                title="New claim received",
                body=f"A claim was submitted for {item.title}.",
                related_item_id=str(item.id),
                related_claim_id=str(claim_id),
            )

        return claim_id
