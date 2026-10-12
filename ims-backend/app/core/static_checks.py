# app/core/static_checks.py - Static bans used by startup and CI (FP-D03, FP-A02)
"""Scan source text for role-key comparisons and migration table names."""

import re
from pathlib import Path

_ROLE_KEY = re.compile(r"""role_key\s*==\s*["']R\d+["']""")
_ADMIN_IN_ROLES = re.compile(r"""["']admin["']\s*in\s*roles""")


def role_key_violations(text: str) -> list[str]:
    """Return the banned snippets present in ``text``."""
    found = []
    if _ROLE_KEY.search(text):
        found.append("role_key")
    if _ADMIN_IN_ROLES.search(text):
        found.append("admin")
    return found


def scan_tree(root: Path) -> list[str]:
    """Scan Python files and return ``path: kind`` hits."""
    hits = []
    for path in root.rglob("*.py"):
        kinds = role_key_violations(path.read_text(encoding="utf-8"))
        for kind in kinds:
            hits.append(f"{path}:{kind}")
    return hits
