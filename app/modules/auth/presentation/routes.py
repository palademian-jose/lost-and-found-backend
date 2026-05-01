from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.lostfound.application.queries.list_audit_logs import (
    ListAuditLogsHandler,
    ListAuditLogsQuery,
)
from app.modules.lostfound.infrastructure.repositories.audit_repo_sql import (
    AuditLogRepositorySQL,
)
from app.modules.lostfound.infrastructure.repositories.notification_repo_sql import (
    NotificationRepositorySQL,
)
from app.shared.infrastructure.db import get_session
from app.shared.infrastructure.rate_limit import rate_limit
from app.shared.infrastructure.settings import settings

from ..application.dtos import to_user_profile_dto
from ..application.commands.moderate_user import (
    SetUserActiveStatusCommand,
    SetUserActiveStatusHandler,
    SetUserRoleCommand,
    SetUserRoleHandler,
)
from ..application.login import LoginCommand, LoginHandler
from ..application.queries.list_users import ListUsersHandler, ListUsersQuery
from ..application.register import RegisterCommand, RegisterHandler
from ..domain.user_role import UserRole
from ..infrastructure.repositories.profile_repo_sql import UserProfileRepositorySQL
from ..infrastructure.repositories.user_repo_sql import UserRepository
from .deps import get_current_user
from .role_guard import require_roles

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    role: UserRole


class RegisterResponse(BaseModel):
    user_id: int
    email: str
    role: UserRole
    is_active: bool


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    user_id: int
    email: str
    role: UserRole
    is_active: bool


class ProfileResponse(BaseModel):
    user_id: int
    full_name: str | None
    phone: str | None
    department: str | None
    preferred_contact_method: str | None


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    department: str | None = None
    preferred_contact_method: str | None = None


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class UpdateUserRoleRequest(BaseModel):
    role: UserRole


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            rate_limit(
                "auth:register",
                limit=settings.auth_register_rate_limit,
                window_seconds=settings.auth_register_rate_window_seconds,
            )
        )
    ],
)
async def register(
    req: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    audit_repo = AuditLogRepositorySQL(session)
    handler = RegisterHandler(repo)

    try:
        user_id = await handler.handle(
            RegisterCommand(
                email=req.email,
                password=req.password,
                role=req.role,
            )
        )
        await audit_repo.add(
            actor_user_id=user_id,
            action="USER_REGISTERED",
            target_type="user",
            target_id=str(user_id),
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
                if str(exc) == "Email already exists."
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    user = await repo.get_by_id(user_id)

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        role=UserRole(user.role),
        is_active=user.is_active,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[
        Depends(
            rate_limit(
                "auth:login",
                limit=settings.auth_login_rate_limit,
                window_seconds=settings.auth_login_rate_window_seconds,
            )
        )
    ],
)
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    handler = LoginHandler(repo)

    try:
        token = await handler.handle(
            LoginCommand(
                email=req.email,
                password=req.password,
            )
        )
        user = await repo.get_by_email(req.email.strip().lower())
        await AuditLogRepositorySQL(session).add(
            actor_user_id=user.id,
            action="USER_LOGGED_IN",
            target_type="user",
            target_id=str(user.id),
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()

        detail = str(exc)
        status_code = status.HTTP_401_UNAUTHORIZED
        if detail == "Your account is inactive.":
            status_code = status.HTTP_403_FORBIDDEN

        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from exc

    return LoginResponse(access_token=token)


@router.get("/me", response_model=CurrentUserResponse)
async def me(user=Depends(get_current_user)):
    return CurrentUserResponse(
        user_id=user.id,
        email=user.email,
        role=UserRole(user.role),
        is_active=user.is_active,
    )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile = await UserProfileRepositorySQL(session).get_dto(user.id)
    return ProfileResponse(**profile.__dict__)


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    req: UpdateProfileRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile = await UserProfileRepositorySQL(session).update(
        user_id=user.id,
        full_name=req.full_name.strip() if req.full_name else None,
        phone=req.phone.strip() if req.phone else None,
        department=req.department.strip() if req.department else None,
        preferred_contact_method=(
            req.preferred_contact_method.strip()
            if req.preferred_contact_method
            else None
        ),
    )
    await session.commit()
    return ProfileResponse(**profile.__dict__)


@router.get("/notifications")
async def list_notifications(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    notifications = await NotificationRepositorySQL(session).list_for_user(user.id)
    return [notification.__dict__ for notification in notifications]


@router.post("/notifications/read-all")
async def mark_notifications_read(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await NotificationRepositorySQL(session).mark_all_read(user.id)
    await session.commit()
    return {"status": "ok"}


@router.get("/protected")
async def protected_test(user=Depends(require_roles([UserRole.ADMIN]))):
    return {
        "message": "Only Admin can access this endpoint",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        },
    }


@admin_router.get("/users")
async def list_users(
    role: UserRole | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user=Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_session),
):
    users = await ListUsersHandler(UserRepository(session)).handle(
        ListUsersQuery(
            role=role,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
    )
    return [asdict(row) for row in users]


@admin_router.patch("/users/{target_user_id}/status")
async def set_user_status(
    target_user_id: int,
    req: UpdateUserStatusRequest,
    admin=Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_session),
):
    try:
        updated_user = await SetUserActiveStatusHandler(
            user_repo=UserRepository(session),
            audit_repo=AuditLogRepositorySQL(session),
        ).handle(
            SetUserActiveStatusCommand(
                actor_user_id=admin.id,
                target_user_id=target_user_id,
                is_active=req.is_active,
            )
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(exc) == "User not found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return {
        "user_id": updated_user.id,
        "email": updated_user.email,
        "role": updated_user.role,
        "is_active": updated_user.is_active,
    }


@admin_router.patch("/users/{target_user_id}/role")
async def set_user_role(
    target_user_id: int,
    req: UpdateUserRoleRequest,
    admin=Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_session),
):
    try:
        updated_user = await SetUserRoleHandler(
            user_repo=UserRepository(session),
            audit_repo=AuditLogRepositorySQL(session),
        ).handle(
            SetUserRoleCommand(
                actor_user_id=admin.id,
                target_user_id=target_user_id,
                role=req.role,
            )
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(exc) == "User not found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return {
        "user_id": updated_user.id,
        "email": updated_user.email,
        "role": updated_user.role,
        "is_active": updated_user.is_active,
    }


@admin_router.get("/audit-logs")
async def list_audit_logs(
    actor_user_id: int | None = None,
    action: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user=Depends(require_roles([UserRole.ADMIN])),
    session: AsyncSession = Depends(get_session),
):
    logs = await ListAuditLogsHandler(
        AuditLogRepositorySQL(session)
    ).handle(
        ListAuditLogsQuery(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            limit=limit,
            offset=offset,
        )
    )
    return [asdict(log) for log in logs]
