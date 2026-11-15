"""Add organizers and editorial metadata, without publishing legacy events.

Revision ID: 0003_event_metadata
Revises: 0002_login_attempts
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_event_metadata"
down_revision = "0002_login_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("public_contact", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_organizers_id", "organizers", ["id"])
    # SQLite needs batch recreation for new FK/CHECK constraints; PostgreSQL
    # performs ALTER TABLE. Existing columns and their values are copied intact.
    with op.batch_alter_table("events") as batch:
        batch.add_column(sa.Column("organizer_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("event_url", sa.String(), nullable=True))
        batch.add_column(sa.Column("source", sa.String(), nullable=True))
        batch.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("publication_status", sa.String(9), nullable=False, server_default="draft"))
        batch.add_column(sa.Column("event_status", sa.String(9), nullable=False, server_default="scheduled"))
        batch.create_foreign_key("fk_events_organizer_id_organizers", "organizers", ["organizer_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_events_organizer_id", ["organizer_id"])
        batch.create_check_constraint("ck_events_publication_status", "publication_status IN ('draft', 'published', 'archived')")
        batch.create_check_constraint("ck_events_event_status", "event_status IN ('scheduled', 'cancelled', 'postponed')")


def downgrade() -> None:
    # DESTRUCTIVE: removes all organizer records and new editorial metadata.
    with op.batch_alter_table("events") as batch:
        batch.drop_constraint("ck_events_event_status", type_="check")
        batch.drop_constraint("ck_events_publication_status", type_="check")
        batch.drop_index("ix_events_organizer_id")
        batch.drop_constraint("fk_events_organizer_id_organizers", type_="foreignkey")
        for column in ("event_status", "publication_status", "verified_at", "source", "event_url", "organizer_id"):
            batch.drop_column(column)
    op.drop_index("ix_organizers_id", table_name="organizers")
    op.drop_table("organizers")
