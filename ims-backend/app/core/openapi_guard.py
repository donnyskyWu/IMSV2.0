# app/core/openapi_guard.py - OpenAPI consistency checks (FP-A05)
"""Compare generated OpenAPI with the committed file and require summaries."""

import json
from typing import Any


def canonical(spec: dict[str, Any]) -> str:
    return json.dumps(spec, ensure_ascii=False, sort_keys=True)


def assert_in_sync(committed: dict[str, Any], generated: dict[str, Any]) -> None:
    """Fail when the committed spec and the generated spec differ."""
    if canonical(committed) != canonical(generated):
        raise RuntimeError("OpenAPI spec out of sync. Run make api-gen")


def assert_summaries(spec: dict[str, Any]) -> None:
    """Every HTTP operation must declare a summary."""
    http = {"get", "post", "put", "patch", "delete"}
    missing = []
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in http:
                continue
            if not operation.get("summary"):
                missing.append(f"{method.upper()} {path}")
    if missing:
        raise RuntimeError(f"routes missing summary: {missing}")


def hardcoded_path(text: str) -> bool:
    """Frontend business files must not hardcode the API prefix."""
    return "/admin-api/ims/" in text
