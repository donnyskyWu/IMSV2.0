# app/core/sensitive_scan.py - Plaintext routes must declare sensitive_view (FP-F02)
"""Fail the route scan when a plaintext response is not marked."""

from typing import Any, Iterable


def scan_sensitive_routes(routes: Iterable[Any]) -> None:
    missing = []
    for route in routes:
        if getattr(route, "returns_plaintext", False) and not getattr(route, "sensitive_view", False):
            missing.append(getattr(route, "path", "?"))
    if missing:
        raise RuntimeError(f"plaintext routes missing sensitive_view: {missing}")
