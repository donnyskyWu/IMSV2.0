# app/integrations/football_live/seed_data.py - Stand-in rows (FP-H06-03)
"""Build eight fake scenarios. Refuses to run when IMS_ENV is prod."""

import os
from typing import Any

SCENARIOS = (
    "not_started",
    "live",
    "ended",
    "paused",
    "deleted",
    "paid",
    "encrypted",
    "playback",
)


def assert_not_prod() -> None:
    if os.environ.get("IMS_ENV") == "prod":
        raise SystemExit(2)


def seed_rooms(store: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Insert each scenario once. A second call does not duplicate rows."""
    assert_not_prod()
    rows = store if store is not None else []
    have = {row["scenario"] for row in rows}
    for index, name in enumerate(SCENARIOS, start=1):
        if name in have:
            continue
        rows.append({
            "id": index,
            "scenario": name,
            "status": index,
            "bind_mobile_password": "fake-secret",
            "login_pwd": "fake-secret",
        })
    return rows
