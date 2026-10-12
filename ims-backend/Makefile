# IMS Backend Makefile
# FP-A05-01: OpenAPI export and frontend client generation

.PHONY: help install lint test coverage api-gen openapi-export api-validate

PYTHON := python3
UVICORN := uvicorn

help:
	@echo "IMS Backend Commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make lint         - Run linting"
	@echo "  make test         - Run tests"
	@echo "  make coverage     - Run tests with coverage"
	@echo "  make api-gen      - Export OpenAPI and generate frontend clients (FP-A05-01)"
	@echo "  make openapi-export - Export openapi.json only"
	@echo "  make api-validate - Validate openapi.json matches current code"

install:
	pip install -e ".[dev]"

lint:
	ruff check app tests
	mypy app

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

# FP-A05-01: OpenAPI export and frontend client generation
# Generates ims-backend/openapi.json and ims-web/src/api/generated/<domain>.ts
api-gen: openapi-export
	@echo "=== Generating frontend TypeScript clients ==="
	$(PYTHON) tools/gen_api_client.py
	@echo "=== API generation complete ==="

# Export OpenAPI spec from running app
openapi-export:
	@echo "=== Exporting OpenAPI specification ==="
	$(PYTHON) tools/export_openapi.py
	@echo "OpenAPI exported to openapi.json"

# Validate openapi.json matches current code (for CI)
api-validate:
	@echo "=== Validating OpenAPI specification ==="
	$(PYTHON) tools/export_openapi.py --validate
	@echo "OpenAPI validation passed"

# Development server
dev:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

migrate-status:
	alembic current
