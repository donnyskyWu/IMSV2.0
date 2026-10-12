# IMS v2.0 Backend
"""
IMS Management System Backend - Python 3.11+ / FastAPI / SQLAlchemy 2.0

Directory structure (per ADR-009 §0.2):
  app/core/        - Config, context, response, error codes, pagination, serialization, security
  app/db/          - Session, base classes, repository, reference registry, tenant/data scope filtering
  app/domains/<domain>/ - model.py, schema.py, repo.py, service.py, router.py
  app/integrations/ - External adapters (dingtalk, football, ai, etc.)
  app/worker/      - Scheduled task entry point
  migrations/      - Alembic (IMS database only)
  tools/scaffold/  - CRUD scaffolding
  tools/football_stub/ - Test stub tables and seeding
  tests/           - pytest tests
"""

__version__ = "2.0.0"
