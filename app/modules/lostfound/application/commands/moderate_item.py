from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.item_repo import ItemRepository


@dataclass
class RemoveItemCommand:
    item_id: UUID
    actor_user_id: int


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
