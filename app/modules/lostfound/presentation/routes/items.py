from dataclasses import asdict
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.user_role import UserRole
from app.modules.auth.presentation.deps import get_current_user
from app.modules.auth.presentation.role_guard import require_roles
from app.shared.infrastructure.db import get_session
from app.shared.infrastructure.rate_limit import rate_limit
from app.shared.infrastructure.settings import settings

from ...application.commands.create_item import CreateItemCommand, CreateItemHandler
from ...application.commands.moderate_item import RemoveItemCommand, RemoveItemHandler
from ...application.commands.submit_claim import SubmitClaimCommand, SubmitClaimHandler
from ...application.queries.get_item_claim_questions import (
    GetItemClaimQuestionsHandler,
    GetItemClaimQuestionsQuery,
)
from ...application.queries.get_item_detail import GetItemDetailHandler, GetItemDetailQuery
from ...application.queries.get_item_management_detail import (
    GetItemManagementDetailHandler,
    GetItemManagementDetailQuery,
)
from ...application.queries.list_item_claims import (
    ListItemClaimsHandler,
    ListItemClaimsQuery,
)
from ...application.queries.list_items import ListItemsHandler, ListItemsQuery
from ...domain.value_objects.item_status import ItemStatus
from ...domain.value_objects.report_type import ReportType
from ...infrastructure.repositories.audit_repo_sql import AuditLogRepositorySQL
from ...infrastructure.repositories.claim_repo_sql import ClaimRepositorySQL
from ...infrastructure.repositories.item_repo_sql import ItemRepositorySQL
from ...infrastructure.repositories.notification_repo_sql import NotificationRepositorySQL


router = APIRouter(tags=["items"])


def _raise_item_error(exc: ValueError) -> None:
    detail = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST

    if "not found" in detail.lower():
        status_code = status.HTTP_404_NOT_FOUND
    elif "only" in detail.lower() or "cannot" in detail.lower():
        status_code = status.HTTP_403_FORBIDDEN

    raise HTTPException(status_code=status_code, detail=detail) from exc


class CreateItemRequest(BaseModel):
    report_type: ReportType
    title: str = Field(min_length=1)
    description_public: str = Field(min_length=1)
    description_private: str | None = None
    category: str = Field(min_length=1)
    location_text: str = Field(min_length=1)
    brand: str | None = None
    color: str | None = None
    happened_at: datetime
    contact_preference: str | None = None
    verification_questions: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)


class SubmitClaimRequest(BaseModel):
    answers: list[str]
    proof_statement: str | None = None


@router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            rate_limit(
                "items:create",
                limit=settings.item_write_rate_limit,
                window_seconds=settings.item_write_rate_window_seconds,
            )
        )
    ],
)
async def create_item(
    req: CreateItemRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    handler = CreateItemHandler(
        item_repo=ItemRepositorySQL(session),
        audit_repo=AuditLogRepositorySQL(session),
    )

    try:
        item_id = await handler.handle(
            CreateItemCommand(
                report_type=req.report_type,
                title=req.title,
                description_public=req.description_public,
                description_private=req.description_private,
                category=req.category,
                location_text=req.location_text,
                brand=req.brand,
                color=req.color,
                happened_at=req.happened_at,
                posted_by_user_id=user.id,
                contact_preference=req.contact_preference,
                verification_questions=req.verification_questions,
                image_urls=req.image_urls,
            )
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        _raise_item_error(exc)

    return {"item_id": str(item_id)}


@router.get("/items")
async def list_items(
    search: Annotated[str | None, Query(alias="q")] = None,
    category: str | None = None,
    status_filter: Annotated[ItemStatus | None, Query(alias="status")] = None,
    report_type: ReportType | None = None,
    posted_by_user_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    handler = ListItemsHandler(ItemRepositorySQL(session))
    items = await handler.handle(
        ListItemsQuery(
            query=search,
            category=category,
            status=status_filter,
            report_type=report_type,
            posted_by_user_id=posted_by_user_id,
            limit=limit,
            offset=offset,
        )
    )

    return [asdict(item) for item in items]


@router.get("/items/{item_id}")
async def get_item_detail(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    handler = GetItemDetailHandler(ItemRepositorySQL(session))
    item = await handler.handle(GetItemDetailQuery(item_id=item_id))

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    public_item = asdict(item)
    public_item.pop("description_private", None)
    return public_item


@router.get("/items/{item_id}/manage")
async def get_item_management_detail(
    item_id: UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    handler = GetItemManagementDetailHandler(ItemRepositorySQL(session))

    try:
        item = await handler.handle(
            GetItemManagementDetailQuery(
                item_id=item_id,
                actor_user_id=user.id,
                is_admin=user.role == UserRole.ADMIN.value,
            )
        )
    except ValueError as exc:
        _raise_item_error(exc)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    return asdict(item)


@router.get("/items/{item_id}/claim-questions")
async def get_item_claim_questions(
    item_id: UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        dto = await GetItemClaimQuestionsHandler(ItemRepositorySQL(session)).handle(
            GetItemClaimQuestionsQuery(
                item_id=item_id,
                actor_user_id=user.id,
            )
        )
    except ValueError as exc:
        _raise_item_error(exc)

    return asdict(dto)


@router.post(
    "/items/{item_id}/claims",
    dependencies=[
        Depends(
            rate_limit(
                "claims:submit",
                limit=settings.claim_submit_rate_limit,
                window_seconds=settings.claim_submit_rate_window_seconds,
            )
        )
    ],
)
async def submit_claim(
    item_id: UUID,
    req: SubmitClaimRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    handler = SubmitClaimHandler(
        item_repo=ItemRepositorySQL(session),
        claim_repo=ClaimRepositorySQL(session),
        audit_repo=AuditLogRepositorySQL(session),
        notification_repo=NotificationRepositorySQL(session),
    )

    try:
        claim_id = await handler.handle(
            SubmitClaimCommand(
                item_id=item_id,
                claimant_user_id=user.id,
                answers=req.answers,
                proof_statement=req.proof_statement,
            )
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        _raise_item_error(exc)

    return {"claim_id": str(claim_id)}


@router.get("/items/{item_id}/claims")
async def list_item_claims(
    item_id: UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    handler = ListItemClaimsHandler(
        item_repo=ItemRepositorySQL(session),
        claim_repo=ClaimRepositorySQL(session),
    )

    try:
        claims = await handler.handle(
            ListItemClaimsQuery(
                item_id=item_id,
                actor_user_id=user.id,
                is_admin=user.role == UserRole.ADMIN.value,
            )
        )
    except ValueError as exc:
        _raise_item_error(exc)

    return [asdict(claim) for claim in claims]


@router.delete("/admin/items/{item_id}")
async def remove_item(
    item_id: UUID,
    user=Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_session),
):
    handler = RemoveItemHandler(
        item_repo=ItemRepositorySQL(session),
        audit_repo=AuditLogRepositorySQL(session),
    )

    try:
        await handler.handle(
            RemoveItemCommand(
                item_id=item_id,
                actor_user_id=user.id,
            )
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        _raise_item_error(exc)

    return {"status": "removed"}
