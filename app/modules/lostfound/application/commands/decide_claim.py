from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ...domain.entities.item import ItemTimelineEvent
from ...domain.repositories.claim_repo import ClaimRepository
from ...domain.repositories.item_repo import ItemRepository


@dataclass
class DecideClaimCommand:
    claim_id: UUID
    decision: str
    actor_user_id: int
    reason: str | None = None


class DecideClaimHandler:
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

    async def handle(self, cmd: DecideClaimCommand):
        claim = await self.claim_repo.get_by_id_for_update(cmd.claim_id)

        if not claim:
            raise ValueError("Claim not found")

        item = await self.item_repo.get_by_id_for_update(claim.item_id)

        if not item:
            raise ValueError("Item not found")

        if item.posted_by_user_id != cmd.actor_user_id:
            raise ValueError("Only item owner can decide this claim")

        if item.active_claim_id != claim.id:
            raise ValueError("Only the active claim can be decided")

        decision = cmd.decision.upper()
        event_time = datetime.now(UTC).replace(tzinfo=None)

        if decision == "APPROVE":
            claim.approve(cmd.reason)
            item.mark_returned()
            item.timeline.append(
                ItemTimelineEvent(
                    event_type="CLAIM_APPROVED",
                    description="The active claim was approved and the item was marked returned.",
                    actor_user_id=cmd.actor_user_id,
                    created_at=event_time,
                )
            )
        elif decision == "REJECT":
            claim.reject(cmd.reason)
            item.reopen()
            item.timeline.append(
                ItemTimelineEvent(
                    event_type="CLAIM_REJECTED",
                    description="The active claim was rejected and the item reopened.",
                    actor_user_id=cmd.actor_user_id,
                    created_at=event_time,
                )
            )
        else:
            raise ValueError("Invalid decision")

        await self.claim_repo.save(claim)
        await self.item_repo.save(item)

        if self.audit_repo is not None:
            await self.audit_repo.add(
                actor_user_id=cmd.actor_user_id,
                action=f"CLAIM_{decision}",
                target_type="claim",
                target_id=str(claim.id),
            )

        if self.notification_repo is not None:
            await self.notification_repo.add(
                user_id=claim.claimant_user_id,
                type=f"CLAIM_{decision}",
                title=f"Claim {decision.title()}",
                body=(
                    f"Your claim for {item.title} was {decision.lower()}."
                    if not cmd.reason
                    else f"Your claim for {item.title} was {decision.lower()}: {cmd.reason}"
                ),
                related_item_id=str(item.id),
                related_claim_id=str(claim.id),
            )
