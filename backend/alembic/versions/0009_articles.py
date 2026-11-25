"""Add blog articles. Does not touch events, organizers or imports."""
from alembic import op
import sqlalchemy as sa

revision = "0009_articles"
down_revision = "0008_event_pricing"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("excerpt", sa.String(500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(500), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("seo_title", sa.String(70), nullable=True),
        sa.Column("seo_description", sa.String(200), nullable=True),
        sa.Column("author_name", sa.String(120), nullable=True),
        sa.Column("publication_status", sa.String(9), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("publication_status IN ('draft','published','archived')",
                           name="ck_articles_publication_status"),
        sa.UniqueConstraint("slug", name="uq_articles_slug"),
    )
    op.create_index("ix_articles_catalog", "articles", ["publication_status", "published_at"])
    op.create_index("ix_articles_category", "articles", ["category"])


def downgrade():
    # DESTRUCTIVE: deletes every blog article. Back up the table first.
    op.drop_index("ix_articles_category", table_name="articles")
    op.drop_index("ix_articles_catalog", table_name="articles")
    op.drop_table("articles")
