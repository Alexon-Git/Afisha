"""Optional absolute event end; existing event instants remain unchanged."""
from alembic import op
import sqlalchemy as sa

revision = "0007_event_end_at"
down_revision = "0006_import_worker_integrity"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("events", sa.Column("end_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Destructive for newly collected end dates; requires a separate backup plan.
    op.drop_column("events", "end_at")
