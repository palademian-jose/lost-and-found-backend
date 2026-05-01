from enum import Enum

class ItemStatus(str, Enum):
    OPEN = "OPEN"
    PENDING = "PENDING"
    RETURNED = "RETURNED"