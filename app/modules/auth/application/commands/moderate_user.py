from dataclasses import dataclass
from typing import Protocol

from app.modules.auth.domain.user_role import UserRole


class UserRepository(Protocol):
    async def get_by_id(self, user_id: int): ...
    async def set_active_status(self, *, user_id: int, is_active: bool): ...
    async def set_role(self, *, user_id: int, role: str): ...
    async def count_active_admins(self) -> int: ...


@dataclass
class SetUserActiveStatusCommand:
    actor_user_id: int
    target_user_id: int
    is_active: bool


@dataclass
class SetUserRoleCommand:
    actor_user_id: int
    target_user_id: int
    role: UserRole


class SetUserActiveStatusHandler:
    def __init__(self, user_repo: UserRepository, audit_repo=None):
        self.user_repo = user_repo
        self.audit_repo = audit_repo

    async def handle(self, cmd: SetUserActiveStatusCommand):
        user = await self.user_repo.get_by_id(cmd.target_user_id)

        if user is None:
            raise ValueError("User not found")

        if user.id == cmd.actor_user_id and not cmd.is_active:
            raise ValueError("You cannot deactivate your own account")

        if (
            user.role == UserRole.ADMIN.value
            and user.is_active
            and not cmd.is_active
            and await self.user_repo.count_active_admins() <= 1
        ):
            raise ValueError("At least one active admin is required")

        updated_user = await self.user_repo.set_active_status(
            user_id=cmd.target_user_id,
            is_active=cmd.is_active,
        )

        if self.audit_repo is not None:
            await self.audit_repo.add(
                actor_user_id=cmd.actor_user_id,
                action="USER_ACTIVATED" if cmd.is_active else "USER_DEACTIVATED",
                target_type="user",
                target_id=str(cmd.target_user_id),
            )

        return updated_user


class SetUserRoleHandler:
    def __init__(self, user_repo: UserRepository, audit_repo=None):
        self.user_repo = user_repo
        self.audit_repo = audit_repo

    async def handle(self, cmd: SetUserRoleCommand):
        user = await self.user_repo.get_by_id(cmd.target_user_id)

        if user is None:
            raise ValueError("User not found")

        if user.id == cmd.actor_user_id and user.role == UserRole.ADMIN.value:
            if cmd.role != UserRole.ADMIN:
                raise ValueError("You cannot remove your own admin role")

        if (
            user.role == UserRole.ADMIN.value
            and user.is_active
            and cmd.role != UserRole.ADMIN
            and await self.user_repo.count_active_admins() <= 1
        ):
            raise ValueError("At least one active admin is required")

        updated_user = await self.user_repo.set_role(
            user_id=cmd.target_user_id,
            role=cmd.role.value,
        )

        if self.audit_repo is not None:
            await self.audit_repo.add(
                actor_user_id=cmd.actor_user_id,
                action="USER_ROLE_UPDATED",
                target_type="user",
                target_id=str(cmd.target_user_id),
            )

        return updated_user
