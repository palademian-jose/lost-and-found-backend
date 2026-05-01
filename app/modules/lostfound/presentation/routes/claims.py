from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.presentation.deps import get_current_user
from app.shared.infrastructure.db import get_session
from app.shared.infrastructure.rate_limit import rate_limit
from app.shared.infrastructure.settings import settings

from ...application.commands.decide_claim import (
    ArrangeHandoverCommand,
    ArrangeHandoverHandler,
    CompleteHandoverCommand,
    CompleteHandoverHandler,
    DecideClaimCommand,
    DecideClaimHandler,
)
from ...application.queries.list_my_claims import ListMyClaimsHandler, ListMyClaimsQuery
from ...infrastructure.repositories.audit_repo_sql import AuditLogRepositorySQL
from ...infrastructure.repositories.claim_repo_sql import ClaimRepositorySQL
from ...infrastructure.repositories.item_repo_sql import ItemRepositorySQL
from ...infrastructure.repositories.notification_repo_sql import NotificationRepositorySQL


router = APIRouter(tags=["claims"])


def _raise_claim_error(exc: ValueError) -> None:
    detail = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST

    if "not found" in detail.lower():
        status_code = status.HTTP_404_NOT_FOUND
    elif "only" in detail.lower():
        status_code = status.HTTP_403_FORBIDDEN

    raise HTTPException(status_code=status_code, detail=detail) from exc


class DecideRequest(BaseModel):
    decision: str
    reason: str | None = None


class ArrangeHandoverRequest(BaseModel):
    handover_note: str


@router.get("/claims/mine")
async def list_my_claims(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    claims = await ListMyClaimsHandler(ClaimRepositorySQL(session)).handle(
        ListMyClaimsQuery(claimant_user_id=user.id)
    )
    return [claim.__dict__ for claim in claims]


@router.post(
    "/claims/{claim_id}/decision",
    dependencies=[
        Depends(
            rate_limit(
                "claims:decision",
                limit=settings.claim_decision_rate_limit,
                window_seconds=settings.claim_decision_rate_window_seconds,
            )
        )
    ],
)
async def decide_claim(
    claim_id: UUID,
    req: DecideRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    handler = DecideClaimHandler(
        item_repo=ItemRepositorySQL(session),
        claim_repo=ClaimRepositorySQL(session),
        audit_repo=AuditLogRepositorySQL(session),
        notification_repo=NotificationRepositorySQL(session),
    )

    try:
        await handler.handle(
            DecideClaimCommand(
                claim_id=claim_id,
                decision=req.decision,
                actor_user_id=user.id,
                reason=req.reason,
            )
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        _raise_claim_error(exc)

    return {"status": "ok"}


@router.post("/claims/{claim_id}/handover")
async def arrange_handover(
    claim_id: UUID,
    req: ArrangeHandoverRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    handler = ArrangeHandoverHandler(
        item_repo=ItemRepositorySQL(session),
        claim_repo=ClaimRepositorySQL(session),
        audit_repo=AuditLogRepositorySQL(session),
        notification_repo=NotificationRepositorySQL(session),
    )

    try:
        await handler.handle(
            ArrangeHandoverCommand(
                claim_id=claim_id,
                actor_user_id=user.id,
                handover_note=req.handover_note,
            )
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        _raise_claim_error(exc)

    return {"status": "handover_arranged"}


@router.post("/claims/{claim_id}/handover/complete")
async def complete_handover(
    claim_id: UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    handler = CompleteHandoverHandler(
        item_repo=ItemRepositorySQL(session),
        claim_repo=ClaimRepositorySQL(session),
        audit_repo=AuditLogRepositorySQL(session),
        notification_repo=NotificationRepositorySQL(session),
    )

    try:
        await handler.handle(
            CompleteHandoverCommand(
                claim_id=claim_id,
                actor_user_id=user.id,
            )
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        _raise_claim_error(exc)

    return {"status": "handover_completed"}
