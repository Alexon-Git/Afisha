"""Initial versioned schema. Existing databases require manual baseline review.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    legacy = existing & {"users", "categories", "events"}
    if legacy:
        raise RuntimeError(
            "Unversioned existing Afisha tables detected: " + ", ".join(sorted(legacy))
            + ". No application tables were changed. Back up the database and "
            "follow backend/MIGRATIONS.md to inspect and baseline it safely."
        )

    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_categories_id", "categories", ["id"])
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)
    op.create_table("events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("datetime", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("creator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("discount", sa.Integer(), nullable=True),
        sa.Column("payment_url", sa.String(), nullable=True),
    )
    op.create_index("ix_events_id", "events", ["id"])
    op.create_index("ix_events_title", "events", ["title"])
    op.create_index("ix_events_datetime", "events", ["datetime"])
    op.create_index("ix_events_category_id", "events", ["category_id"])

def downgrade() -> None:
    # DESTRUCTIVE. Back up data first.
    op.drop_index("ix_events_category_id", table_name="events")
    op.drop_index("ix_events_datetime", table_name="events")
    op.drop_index("ix_events_title", table_name="events")
    op.drop_index("ix_events_id", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_index("ix_categories_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
