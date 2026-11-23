"""Require empty events, then enable the absolute UTC datetime contract.

Existing rows deliberately block conversion; no historical timezone is guessed.
SQLite stores UTC components; the application restores an explicit UTC offset.
"""
from alembic import context, op
import sqlalchemy as sa

revision = "0004_event_datetime_utc"
down_revision = "0003_event_metadata"
branch_labels = None
depends_on = None


def upgrade():
    if context.is_offline_mode():
        raise RuntimeError("PR-8 requires an online empty-events check")
    connection = op.get_bind()
    dialect = connection.dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        raise RuntimeError("Unsupported database for event datetime migration")
    # Hold the lock until transaction commit: no concurrent insert can race
    # the empty-table check and type conversion. Fail instead of waiting forever.
    if dialect == "postgresql":
        connection.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(sa.text("LOCK TABLE events IN ACCESS EXCLUSIVE MODE"))
    elif not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    if connection.execute(sa.text("SELECT 1 FROM events LIMIT 1")).first() is not None:
        raise RuntimeError("PR-8 BLOCKED: existing event datetimes need source/timezone verification")
    column = next(c for c in sa.inspect(connection).get_columns("events") if c["name"] == "datetime")
    if not isinstance(column["type"], sa.DateTime) or column["type"].timezone:
        raise RuntimeError("Unexpected events.datetime type; inspect schema before migration")
    if dialect == "sqlite":
        return  # SQLite has no timezone type; UTCDateTime owns its encoding.
    op.alter_column(
        "events", "datetime", existing_type=sa.DateTime(timezone=False),
        type_=sa.DateTime(timezone=True), existing_nullable=False,
        # Empty table only. UTC is explicit so the DDL never depends on the
        # session TimeZone; it is NOT a policy for historical naive values.
        postgresql_using="datetime AT TIME ZONE 'UTC'",
    )


def downgrade():
    raise RuntimeError("PR-8 downgrade requires an explicit backup/export and timezone plan")
