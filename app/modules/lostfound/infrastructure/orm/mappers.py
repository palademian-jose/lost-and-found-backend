from uuid import UUID

from ...domain.entities.claim import Claim
from ...domain.entities.item import Item, ItemImage, ItemTimelineEvent, VerificationQuestion
from ...domain.value_objects.claim_status import ClaimStatus
from ...domain.value_objects.item_status import ItemStatus
from ...domain.value_objects.report_type import ReportType
from .models import ClaimModel, ItemModel


def map_item_model_to_domain(model: ItemModel) -> Item:
    return Item(
        id=UUID(model.id),
        report_type=ReportType(model.report_type),
        title=model.title,
        description_public=model.description_public,
        description_private=model.description_private,
        category=model.category,
        location_text=model.location_text,
        brand=model.brand,
        color=model.color,
        happened_at=model.happened_at,
        posted_by_user_id=model.posted_by_user_id,
        contact_preference=model.contact_preference,
        status=ItemStatus(model.status),
        verification_questions=[
            VerificationQuestion(question.question)
            for question in model.verification_questions
        ],
        images=[
            ItemImage(
                image_url=image.image_url,
                is_primary=image.is_primary,
                sort_order=image.sort_order,
            )
            for image in model.images
        ],
        timeline=[
            ItemTimelineEvent(
                event_type=event.event_type,
                description=event.description,
                actor_user_id=event.actor_user_id,
                created_at=event.created_at,
            )
            for event in model.timeline_events
        ],
        active_claim_id=UUID(model.active_claim_id) if model.active_claim_id else None,
        resolved_at=model.resolved_at,
    )


def map_claim_model_to_domain(model: ClaimModel) -> Claim:
    return Claim(
        id=UUID(model.id),
        item_id=UUID(model.item_id),
        claimant_user_id=model.claimant_user_id,
        answers=[answer.answer for answer in model.answers],
        proof_statement=model.proof_statement,
        status=ClaimStatus(model.status),
        submitted_at=model.submitted_at,
        decision_reason=model.decision_reason,
        decided_at=model.decided_at,
        handover_note=model.handover_note,
        handover_arranged_at=model.handover_arranged_at,
        handed_over_at=model.handed_over_at,
    )
