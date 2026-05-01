from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserSummaryDTO:
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime


@dataclass
class UserProfileDTO:
    user_id: int
    full_name: str | None
    phone: str | None
    department: str | None
    preferred_contact_method: str | None
    created_at: datetime
    updated_at: datetime


def to_user_summary_dto(user) -> UserSummaryDTO:
    return UserSummaryDTO(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def to_user_profile_dto(profile) -> UserProfileDTO:
    return UserProfileDTO(
        user_id=profile.user_id,
        full_name=profile.full_name,
        phone=profile.phone,
        department=profile.department,
        preferred_contact_method=profile.preferred_contact_method,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
