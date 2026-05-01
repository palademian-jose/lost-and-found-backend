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
    handover_note: str | None = None
    handover_arranged_at: datetime | None = None
    handed_over_at: datetime | None = None

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

    def arrange_handover(self, handover_note: str):
        if self.status != ClaimStatus.APPROVED:
            raise ValueError("Only approved claims can have handover arranged.")
        note = handover_note.strip()
        if not note:
            raise ValueError("Handover note is required.")
        self.status = ClaimStatus.HANDOVER_ARRANGED
        self.handover_note = note
        self.handover_arranged_at = datetime.now(UTC).replace(tzinfo=None)

    def complete_handover(self):
        if self.status != ClaimStatus.HANDOVER_ARRANGED:
            raise ValueError("Only arranged handovers can be completed.")
        self.status = ClaimStatus.HANDED_OVER
        self.handed_over_at = datetime.now(UTC).replace(tzinfo=None)
