from enum import Enum


class ReportType(str, Enum):
    LOST = "LOST"
    FOUND = "FOUND"
