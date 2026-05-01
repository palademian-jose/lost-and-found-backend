from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ...domain.entities.item import Item, ItemTimelineEvent
from ...domain.repositories.item_repo import ItemRepository
from ...domain.value_objects.report_type import ReportType


@dataclass
class CreateItemCommand:
    report_type: ReportType
    title: str
    description_public: str
    description_private: str | None
    category: str
    location_text: str
    brand: str | None
    color: str | None
    happened_at: datetime
    posted_by_user_id: int
    contact_preference: str | None
    verification_questions: list[str]
    image_urls: list[str]


class CreateItemHandler:
    def __init__(self, item_repo: ItemRepository, audit_repo=None):
        self.item_repo = item_repo
        self.audit_repo = audit_repo

    async def handle(self, cmd: CreateItemCommand) -> UUID:
        item = Item.create(
            report_type=cmd.report_type,
            title=cmd.title,
            description_public=cmd.description_public,
            description_private=cmd.description_private,
            category=cmd.category,
            location_text=cmd.location_text,
            brand=cmd.brand,
            color=cmd.color,
            happened_at=cmd.happened_at,
            posted_by_user_id=cmd.posted_by_user_id,
            contact_preference=cmd.contact_preference,
            verification_questions=cmd.verification_questions,
            image_urls=cmd.image_urls,
        )

        item.timeline.append(
            ItemTimelineEvent(
                event_type="ITEM_CREATED",
                description=f"{cmd.report_type.value.title()} item report created.",
                actor_user_id=cmd.posted_by_user_id,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )

        await self.item_repo.save(item)

        if self.audit_repo is not None:
            await self.audit_repo.add(
                actor_user_id=cmd.posted_by_user_id,
                action="ITEM_CREATED",
                target_type="item",
                target_id=str(item.id),
            )

        return item.id
