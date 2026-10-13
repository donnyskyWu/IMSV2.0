# app/db/json_query.py - portable JSON array membership
"""JSON array containment that works on MySQL and SQLite."""

from typing import Any

from sqlalchemy import exists, func, literal, select
from sqlalchemy.sql.elements import ColumnElement


def json_array_contains(
    column: Any,
    path: str,
    value: int,
    dialect: str,
) -> ColumnElement[bool]:
    """True when the JSON array at ``path`` contains ``value``.

    MySQL uses JSON_CONTAINS. SQLite uses json_each, which the test database provides.
    """
    if dialect == "sqlite":
        extracted = func.json_extract(column, path)
        entries = func.json_each(extracted).table_valued("value")
        return exists(select(literal(1)).where(entries.c.value == value))

    return func.json_contains(column, literal(str(value)), literal(path))
