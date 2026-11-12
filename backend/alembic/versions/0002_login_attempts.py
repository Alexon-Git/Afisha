"""Add shared login rate-limit counters without changing users.

Revision ID: 0002_login_attempts
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_login_attempts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("key", sa.String(72), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_login_attempts_expires_at", "login_attempts", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_login_attempts_expires_at", table_name="login_attempts")
    op.drop_table("login_attempts")
