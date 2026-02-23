"""Initial schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("ADMIN", "ANALYST", "DEVELOPER", "VIEWER", "RESTRICTED", name="userrole"), nullable=False),
        sa.Column("allowed_tables", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("daily_query_limit", sa.Integer(), nullable=False),
        sa.Column("queries_today", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "query_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=False),
        sa.Column("sql_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("governance_decision", sa.Enum("APPROVED", "REQUIRES_APPROVAL", "DENIED", name="governancedecisiontype"), nullable=False),
        sa.Column("governance_reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", "EXECUTED", "FAILED", name="querystatus"), nullable=False),
        sa.Column("result_row_count", sa.Integer()),
        sa.Column("execution_time_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_request_id", sa.Integer(), sa.ForeignKey("query_requests.id"), nullable=False, unique=True),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", name="approvalstatus"), nullable=False),
        sa.Column("reviewer_comment", sa.Text()),
        sa.Column("timeout_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("query_request_id", sa.Integer(), sa.ForeignKey("query_requests.id")),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ip_address", sa.String(length=64)),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "travel_planner",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org", sa.String(length=255), nullable=False),
        sa.Column("dest", sa.String(length=255), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("date", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=64), nullable=False),
        sa.Column("reference_information", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("travel_planner")
    op.drop_table("audit_logs")
    op.drop_table("approval_requests")
    op.drop_table("query_requests")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
