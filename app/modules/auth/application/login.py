from dataclasses import dataclass
from typing import Protocol

from app.modules.auth.infrastructure.security.password import verify_password
from app.modules.auth.infrastructure.security.jwt import create_access_token


class UserRepository(Protocol):
    async def get_by_email(self, email: str): ...


@dataclass
class LoginCommand:
    email: str
    password: str


class LoginHandler:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def handle(self, cmd: LoginCommand) -> str:
        email = cmd.email.strip().lower()

        if not email or not cmd.password:
            raise ValueError("Invalid email or password.")

        user = await self.user_repo.get_by_email(email)

        if not user:
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("Your account is inactive.")

        if not verify_password(cmd.password, user.password_hash):
            raise ValueError("Invalid email or password.")

        token = create_access_token(
            subject=str(user.id),
            role=user.role,
        )

        return token
