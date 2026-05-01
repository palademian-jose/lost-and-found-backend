from enum import Enum

class UserRole(str, Enum):
    MEMBER = "MEMBER"
    ADMIN = "ADMIN"
