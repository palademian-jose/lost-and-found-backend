from dataclasses import dataclass
from typing import Protocol

from app.modules.auth.domain.user_role import UserRole
from app.modules.auth.infrastructure.security.password import hash_password


class UserRepository(Protocol):
    async def get_by_email(self, email: str): ...
    async def create(self, *, email: str, password_hash: str, role: str): ...


@dataclass
class RegisterCommand:
    email: str
    password: str
    role: UserRole


class RegisterHandler:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def handle(self, cmd: RegisterCommand) -> int:
        email = cmd.email.strip().lower()

        if not email or not cmd.password:
            raise ValueError("Email and password are required.")

        if len(cmd.password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        if cmd.role == UserRole.ADMIN:
            raise ValueError("Admin accounts cannot be self-registered.")

        existing_user = await self.user_repo.get_by_email(email)

        if existing_user:
            raise ValueError("Email already exists.")

        user = await self.user_repo.create(
            email=email,
            password_hash=hash_password(cmd.password),
            role=cmd.role.value,
        )

        return user.id
