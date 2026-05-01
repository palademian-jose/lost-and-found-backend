from dataclasses import dataclass
from datetime import datetime

from ..domain.entities.claim import Claim
from ..domain.entities.item import Item


@dataclass
class ItemSummaryDTO:
    id: str
    report_type: str
    title: str
    description_public: str
    brand: str | None
    color: str | None
    category: str
    location_text: str
    image_urls: list[str]
    happened_at: datetime
    status: str


@dataclass
class ItemDetailDTO(ItemSummaryDTO):
    description_private: str | None
    contact_preference: str | None
    timeline: list[dict]
    resolved_at: datetime | None


@dataclass
class ManagedItemDetailDTO(ItemDetailDTO):
    posted_by_user_id: int
    verification_questions: list[str]
    active_claim_id: str | None


@dataclass
class ClaimReviewDTO:
    id: str
    item_id: str
    claimant_user_id: int
    answers: list[str]
    proof_statement: str | None
    status: str
    submitted_at: datetime
    decision_reason: str | None
    decided_at: datetime | None
    handover_note: str | None
    handover_arranged_at: datetime | None
    handed_over_at: datetime | None


@dataclass
class ClaimQuestionsDTO:
    item_id: str
    questions: list[str]


@dataclass
class AuditLogDTO:
    id: int
    actor_user_id: int
    action: str
    target_type: str
    target_id: str
    created_at: datetime


@dataclass
class NotificationDTO:
    id: int
    user_id: int
    type: str
    title: str
    body: str
    is_read: bool
    related_item_id: str | None
    related_claim_id: str | None
    created_at: datetime


def to_item_summary_dto(item: Item) -> ItemSummaryDTO:
    return ItemSummaryDTO(
        id=str(item.id),
        report_type=item.report_type.value,
        title=item.title,
        description_public=item.description_public,
        brand=item.brand,
        color=item.color,
        category=item.category,
        location_text=item.location_text,
        image_urls=[image.image_url for image in item.images],
        happened_at=item.happened_at,
        status=item.status.value,
    )


def to_item_detail_dto(item: Item) -> ItemDetailDTO:
    return ItemDetailDTO(
        **to_item_summary_dto(item).__dict__,
        description_private=item.description_private,
        contact_preference=item.contact_preference,
        timeline=[
            {
                "event_type": event.event_type,
                "description": event.description,
                "actor_user_id": event.actor_user_id,
                "created_at": event.created_at,
            }
            for event in item.timeline
        ],
        resolved_at=item.resolved_at,
    )


def to_managed_item_detail_dto(item: Item) -> ManagedItemDetailDTO:
    return ManagedItemDetailDTO(
        **to_item_detail_dto(item).__dict__,
        posted_by_user_id=item.posted_by_user_id,
        verification_questions=[
            question.question
            for question in item.verification_questions
        ],
        active_claim_id=str(item.active_claim_id) if item.active_claim_id else None,
    )


def to_claim_review_dto(claim: Claim) -> ClaimReviewDTO:
    return ClaimReviewDTO(
        id=str(claim.id),
        item_id=str(claim.item_id),
        claimant_user_id=claim.claimant_user_id,
        answers=claim.answers,
        proof_statement=claim.proof_statement,
        status=claim.status.value,
        submitted_at=claim.submitted_at,
        decision_reason=claim.decision_reason,
        decided_at=claim.decided_at,
        handover_note=claim.handover_note,
        handover_arranged_at=claim.handover_arranged_at,
        handed_over_at=claim.handed_over_at,
    )


def to_claim_questions_dto(item: Item) -> ClaimQuestionsDTO:
    return ClaimQuestionsDTO(
        item_id=str(item.id),
        questions=[question.question for question in item.verification_questions],
    )


def to_audit_log_dto(model) -> AuditLogDTO:
    return AuditLogDTO(
        id=model.id,
        actor_user_id=model.actor_user_id,
        action=model.action,
        target_type=model.target_type,
        target_id=model.target_id,
        created_at=model.created_at,
    )


def to_notification_dto(model) -> NotificationDTO:
    return NotificationDTO(
        id=model.id,
        user_id=model.user_id,
        type=model.type,
        title=model.title,
        body=model.body,
        is_read=model.is_read,
        related_item_id=model.related_item_id,
        related_claim_id=model.related_claim_id,
        created_at=model.created_at,
    )
