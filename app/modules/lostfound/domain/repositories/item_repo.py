from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from ..entities.item import Item
from ..value_objects.item_status import ItemStatus
from ..value_objects.report_type import ReportType


@dataclass
class ItemListFilters:
    query: str | None = None
    category: str | None = None
    status: ItemStatus | None = None
    report_type: ReportType | None = None
    posted_by_user_id: int | None = None
    limit: int = 100
    offset: int = 0


class ItemRepository(ABC):
    @abstractmethod
    async def get_by_id(self, item_id: UUID) -> Optional[Item]:
        pass

    @abstractmethod
    async def get_by_id_for_update(self, item_id: UUID) -> Optional[Item]:
        pass

    @abstractmethod
    async def save(self, item: Item) -> None:
        pass

    @abstractmethod
    async def delete(self, item_id: UUID) -> None:
        pass

    @abstractmethod
    async def list(self, filters: ItemListFilters) -> list[Item]:
        pass
