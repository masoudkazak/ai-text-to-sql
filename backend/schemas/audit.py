"""Audit schemas."""

from datetime import datetime

from pydantic import BaseModel


class AuditOut(BaseModel):
    id: int
    user_id: int
    query_request_id: int | None
    event_type: str
    details: dict
    ip_address: str | None
    timestamp: datetime
