from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ...domain.entities.item import ItemTimelineEvent
from ...domain.repositories.item_repo import ItemRepository


@dataclass
class RemoveItemCommand:
    item_id: UUID
    actor_user_id: int


@dataclass
class MarkItemReturnedCommand:
    item_id: UUID
    actor_user_id: int
    is_admin: bool = False


class RemoveItemHandler:
    def __init__(self, item_repo: ItemRepository, audit_repo=None):
        self.item_repo = item_repo
        self.audit_repo = audit_repo

    async def handle(self, cmd: RemoveItemCommand):
        item = await self.item_repo.get_by_id(cmd.item_id)

        if not item:
            raise ValueError("Item not found")

        await self.item_repo.delete(item.id)

        if self.audit_repo is not None:
            await self.audit_repo.add(
                actor_user_id=cmd.actor_user_id,
                action="ITEM_REMOVED",
                target_type="item",
                target_id=str(item.id),
            )


class MarkItemReturnedHandler:
    def __init__(self, item_repo: ItemRepository, audit_repo=None):
        self.item_repo = item_repo
        self.audit_repo = audit_repo

    async def handle(self, cmd: MarkItemReturnedCommand):
        item = await self.item_repo.get_by_id_for_update(cmd.item_id)

        if not item:
            raise ValueError("Item not found")

        if not cmd.is_admin and item.posted_by_user_id != cmd.actor_user_id:
            raise ValueError("Only the post owner can mark this item returned")

        item.mark_returned_without_claim()
        item.timeline.append(
            ItemTimelineEvent(
                event_type="ITEM_RETURNED_BY_OWNER",
                description="The reporter marked this item as returned without a claim.",
                actor_user_id=cmd.actor_user_id,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await self.item_repo.save(item)

        if self.audit_repo is not None:
            await self.audit_repo.add(
                actor_user_id=cmd.actor_user_id,
                action="ITEM_MARKED_RETURNED",
                target_type="item",
                target_id=str(item.id),
            )
