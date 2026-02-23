"""Query request model."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.enums import GovernanceDecisionType, QueryStatus


class QueryRequest(Base):
    """Text to SQL request."""

    __tablename__ = "query_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str] = mapped_column(Text, nullable=False)
    sql_analysis: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    governance_decision: Mapped[GovernanceDecisionType] = mapped_column(Enum(GovernanceDecisionType), nullable=False)
    governance_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[QueryStatus] = mapped_column(Enum(QueryStatus), default=QueryStatus.PENDING, nullable=False)
    result_row_count: Mapped[int | None] = mapped_column(Integer)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User")
