"""Approval schemas."""

from datetime import datetime

from pydantic import BaseModel


class ApprovalDecisionIn(BaseModel):
    query_request_id: int
    approve: bool
    comment: str | None = None


class ApprovalOut(BaseModel):
    id: int
    query_request_id: int
    reviewer_id: int | None
    status: str
    reviewer_comment: str | None
    timeout_at: datetime | None
    created_at: datetime
    decided_at: datetime | None
