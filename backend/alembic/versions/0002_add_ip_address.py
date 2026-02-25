"""Add ip_address column to users table."""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_ip_address"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ip_address", sa.String(length=45), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ip_address")
