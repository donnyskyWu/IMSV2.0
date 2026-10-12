# app/integrations/football_live/schema.py - DDL schema guard (FP-H06-02)
"""Compare a stand-in schema with the real Football DDL."""

import re
from pathlib import Path

_COL = re.compile(r"`(\w+)`\s+([a-zA-Z]+)")


def ddl_path() -> Path:
    return (
        Path(__file__).resolve().parents[4]
        / "docs"
        / "ims-v2-rewrite"
        / "modules"
        / "B0a-框架"
        / "live_room-真实DDL.sql"
    )


def parse_columns(sql: str) -> dict[str, str]:
    """Map column name to a normalized type token."""
    columns: dict[str, str] = {}
    for name, raw_type in _COL.findall(sql):
        columns[name] = raw_type.lower()
    return columns


def baseline_columns() -> dict[str, str]:
    return parse_columns(ddl_path().read_text(encoding="utf-8"))


def schema_diffs(actual: dict[str, str], expected: dict[str, str] | None = None) -> list[str]:
    """List missing columns and type mismatches against the real DDL."""
    wanted = expected if expected is not None else baseline_columns()
    diffs: list[str] = []
    for name, type_name in wanted.items():
        if name not in actual:
            diffs.append(f"missing {name}")
            continue
        if actual[name] != type_name:
            diffs.append(f"{name} {actual[name]} != {type_name}")
    return diffs


def assert_startup_schema(actual: dict[str, str]) -> None:
    diffs = schema_diffs(actual)
    if diffs:
        raise RuntimeError("football schema diff: " + "; ".join(diffs))
