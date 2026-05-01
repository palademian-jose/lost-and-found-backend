from fastapi import Depends, HTTPException
from typing import Iterable

from .deps import get_current_user
from ..domain.user_role import UserRole


def require_roles(roles: Iterable[UserRole]):

    async def checker(user=Depends(get_current_user)):

        # convert enum list -> string list
        allowed_roles = [r.value for r in roles]
        
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions",
            )
        return user

    return checker