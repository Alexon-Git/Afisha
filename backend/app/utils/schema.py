"""Helpers for inspecting and amending database schemas at runtime."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ColumnRequirement:
    """Describe a column that should exist on a database table."""

    table: str
    column: str
    definition: str
    schema: str | None = None


def _quoted(identifier: str) -> str:
    """Return an SQL identifier quoted for safe interpolation."""

    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def ensure_column(
    engine: Engine,
    table_name: str,
    column_name: str,
    column_definition: str,
    *,
    schema: str | None = None,
) -> None:
    """Ensure that a particular column exists on the target table.

    This helper introspects the database and adds the column if it is missing. The
    column definition should only contain the type/constraints segment (e.g.
    ``"VARCHAR"`` or ``"BOOLEAN DEFAULT FALSE"``).
    """

    inspector = inspect(engine)
    try:
        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name, schema=schema)
        }
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Could not inspect table %s%s: %s",
            f"{schema}." if schema else "",
            table_name,
            exc,
        )
        return

    if column_name in existing_columns:
        return

    qualified_table = _quoted(table_name)
    if schema:
        qualified_table = f"{_quoted(schema)}.{qualified_table}"

    ddl = text(
        f"ALTER TABLE {qualified_table} ADD COLUMN {_quoted(column_name)} {column_definition}"
    )

    try:
        with engine.begin() as connection:
            connection.execute(ddl)
            logger.info(
                "Added missing column %s.%s", schema + "." if schema else "", column_name
            )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Could not add column %s.%s: %s",
            schema + "." if schema else "",
            column_name,
            exc,
        )


def ensure_columns(engine: Engine, requirements: Iterable[ColumnRequirement]) -> None:
    """Ensure a collection of column requirements are satisfied."""

    for requirement in requirements:
        ensure_column(
            engine,
            requirement.table,
            requirement.column,
            requirement.definition,
            schema=requirement.schema,
        )
