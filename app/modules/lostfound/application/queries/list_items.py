from dataclasses import dataclass

from ...domain.repositories.item_repo import ItemListFilters, ItemRepository
from ...domain.value_objects.item_status import ItemStatus
from ...domain.value_objects.report_type import ReportType
from ..dtos import ItemSummaryDTO, to_item_summary_dto


@dataclass
class ListItemsQuery:
    query: str | None = None
    category: str | None = None
    status: ItemStatus | None = None
    report_type: ReportType | None = None
    posted_by_user_id: int | None = None
    limit: int = 100
    offset: int = 0


class ListItemsHandler:
    def __init__(self, item_repo: ItemRepository):
        self.item_repo = item_repo

    async def handle(self, query: ListItemsQuery) -> list[ItemSummaryDTO]:
        items = await self.item_repo.list(
            ItemListFilters(
                query=query.query,
                category=query.category,
                status=query.status,
                report_type=query.report_type,
                posted_by_user_id=query.posted_by_user_id,
                limit=query.limit,
                offset=query.offset,
            )
        )

        return [to_item_summary_dto(item) for item in items]
