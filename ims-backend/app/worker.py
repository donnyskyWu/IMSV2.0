# app/worker.py - Worker process without HTTP routes (FP-A01-05)
"""Worker tasks share model classes with the API process and expose no routes."""

from typing import Any

from app.jobs import JOBS, job


@job
def sync_retry() -> None:
    """Sample registered task."""
    return None


def _register_domain_jobs() -> None:
    """导入带 @job 的业务函数，完成登记。"""
    from app.services import cert_expire  # noqa: F401


_register_domain_jobs()


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
