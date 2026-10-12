# app/worker.py - Worker process without HTTP routes (FP-A01-05)
"""Worker tasks share model classes with the API process and expose no routes."""

from typing import Any

JOBS: list[str] = []


def job(fn: Any) -> Any:
    """Register a worker task."""
    JOBS.append(fn.__name__)
    return fn


@job
def sync_retry() -> None:
    """Sample registered task."""
    return None


class WorkerProcess:
    """Process that runs ``@job`` tasks and does not mount HTTP routes."""

    def http_routes(self) -> list[str]:
        return []

    def tasks(self) -> list[str]:
        return list(JOBS)


def model_user() -> Any:
    """Return the same User class the API process imports."""
    from app.domains.sys.models import User

    return User
