from dataclasses import dataclass
from datetime import datetime

from .user_role import UserRole


@dataclass
class User:
    id: int
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    created_at: datetime
