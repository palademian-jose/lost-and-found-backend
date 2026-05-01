from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID, uuid4

from ..value_objects.item_status import ItemStatus
from ..value_objects.report_type import ReportType


@dataclass
class VerificationQuestion:
    question: str


@dataclass
class ItemImage:
    image_url: str
    is_primary: bool = False
    sort_order: int = 0


@dataclass
class ItemTimelineEvent:
    event_type: str
    description: str
    actor_user_id: int | None
    created_at: datetime


@dataclass
class Item:
    id: UUID
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
    contact_preference: str | None = None
    status: ItemStatus = ItemStatus.OPEN
    verification_questions: List[VerificationQuestion] = field(default_factory=list)
    images: List[ItemImage] = field(default_factory=list)
    timeline: List[ItemTimelineEvent] = field(default_factory=list)
    active_claim_id: Optional[UUID] = None
    resolved_at: Optional[datetime] = None

    @staticmethod
    def create(
        report_type: ReportType | str,
        title: str,
        description_public: str,
        description_private: str | None,
        category: str,
        location_text: str,
        brand: str | None,
        color: str | None,
        happened_at: datetime,
        posted_by_user_id: int,
        contact_preference: str | None,
        verification_questions: List[str],
        image_urls: List[str],
    ) -> "Item":
        normalized_questions = [
            question.strip()
            for question in verification_questions
            if question.strip()
        ]
        normalized_image_urls = [
            image_url.strip()
            for image_url in image_urls
            if image_url.strip()
        ]

        if not title.strip():
            raise ValueError("Title is required.")

        if not description_public.strip():
            raise ValueError("Description is required.")

        if not category.strip():
            raise ValueError("Category is required.")

        if not location_text.strip():
            raise ValueError("Location is required.")

        if not normalized_questions:
            raise ValueError("At least one verification question is required.")

        normalized_happened_at = happened_at
        if normalized_happened_at.tzinfo is not None:
            normalized_happened_at = normalized_happened_at.astimezone(UTC).replace(
                tzinfo=None
            )

        return Item(
            id=uuid4(),
            report_type=ReportType(report_type),
            title=title.strip(),
            description_public=description_public.strip(),
            description_private=description_private.strip() if description_private else None,
            category=category.strip(),
            location_text=location_text.strip(),
            brand=brand.strip() if brand else None,
            color=color.strip() if color else None,
            happened_at=normalized_happened_at,
            posted_by_user_id=posted_by_user_id,
            contact_preference=contact_preference.strip() if contact_preference else None,
            status=ItemStatus.OPEN,
            verification_questions=[
                VerificationQuestion(question)
                for question in normalized_questions
            ],
            images=[
                ItemImage(image_url=image_url, is_primary=index == 0, sort_order=index)
                for index, image_url in enumerate(normalized_image_urls)
            ],
            timeline=[],
            active_claim_id=None,
            resolved_at=None,
        )

    def mark_pending(self, claim_id: UUID) -> None:
        if self.status != ItemStatus.OPEN:
            raise ValueError("Item must be OPEN to accept a claim.")
        self.status = ItemStatus.PENDING
        self.active_claim_id = claim_id

    def mark_returned(self) -> None:
        if self.status != ItemStatus.PENDING:
            raise ValueError("Item must be PENDING to be marked RETURNED.")
        self.status = ItemStatus.RETURNED
        self.resolved_at = datetime.now(UTC).replace(tzinfo=None)

    def reopen(self) -> None:
        if self.status != ItemStatus.PENDING:
            raise ValueError("Item must be PENDING to reopen.")
        self.status = ItemStatus.OPEN
        self.active_claim_id = None
        self.resolved_at = None
