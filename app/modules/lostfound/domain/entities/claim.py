from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ..value_objects.claim_status import ClaimStatus


@dataclass
class Claim:
    id: UUID
    item_id: UUID
    claimant_user_id: int
    answers: list[str]
    proof_statement: str | None
    status: ClaimStatus
    submitted_at: datetime
    decision_reason: str | None = None
    decided_at: datetime | None = None

    def approve(self, decision_reason: str | None = None):
        if self.status != ClaimStatus.SUBMITTED:
            raise ValueError("Only submitted claims can be approved.")
        self.status = ClaimStatus.APPROVED
        self.decision_reason = decision_reason.strip() if decision_reason else None
        self.decided_at = datetime.now(UTC).replace(tzinfo=None)

    def reject(self, decision_reason: str | None = None):
        if self.status != ClaimStatus.SUBMITTED:
            raise ValueError("Only submitted claims can be rejected.")
        self.status = ClaimStatus.REJECTED
        self.decision_reason = decision_reason.strip() if decision_reason else None
        self.decided_at = datetime.now(UTC).replace(tzinfo=None)
