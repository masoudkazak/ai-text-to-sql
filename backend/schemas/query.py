"""Query schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class QueryInput(BaseModel):
    text: str


class SQLAnalysis(BaseModel):
    query_type: str
    tables_accessed: list[str]
    has_where_clause: bool
    is_read_only: bool
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    sensitive_columns_found: list[str]
    estimated_affected_rows: Literal["unknown", "few", "many", "all"]
    injection_patterns: list[str] = []


class GovernanceDecision(BaseModel):
    decision: Literal["APPROVED", "REQUIRES_APPROVAL", "DENIED"]
    reason: str
    risk_level: str
    mask_columns: list[str]


class QueryResponse(BaseModel):
    query_request_id: int
    generated_sql: str
    sql_analysis: SQLAnalysis
    governance: GovernanceDecision
    status: str
    result: list[dict[str, Any]] | None = None
    created_at: datetime
