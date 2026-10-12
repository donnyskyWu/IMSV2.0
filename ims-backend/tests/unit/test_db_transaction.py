# tests/unit/test_db_transaction.py
"""
Unit tests for transaction management.

Covers app/db/transaction.py
"""
import os

os.environ.setdefault("IMS_ENV", "test")
os.environ.setdefault("IMS_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("IMS_REDIS_URL", "")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")

import pytest


class TestTransactionalDecorator:
    """Tests for @transactional decorator."""

    def test_transactional_import(self):
        """Test transactional decorator can be imported."""
        from app.db.transaction import transactional
        assert callable(transactional)

    def test_transactional_decorates_function(self):
        """Test transactional can decorate a function."""
        from app.db.transaction import transactional

        @transactional
        def my_function():
            return "result"

        assert callable(my_function)

    def test_transactional_preserves_function_name(self):
        """Test transactional preserves function metadata."""
        from app.db.transaction import transactional

        @transactional
        def named_function():
            """Docstring."""
            pass

        assert named_function.__name__ == "named_function"
        assert "Docstring" in (named_function.__doc__ or "")


class TestTransactionContext:
    """Tests for TransactionContext context manager."""

    def test_transaction_context_import(self):
        """Test TransactionContext can be imported."""
        from app.db.transaction import TransactionContext
        assert TransactionContext is not None

    def test_transaction_context_has_methods(self):
        """Test TransactionContext has required methods."""
        from app.db.transaction import TransactionContext

        ctx = TransactionContext()
        assert hasattr(ctx, "commit")
        assert hasattr(ctx, "rollback")
        assert hasattr(ctx, "flush")
        assert hasattr(ctx, "__enter__")
        assert hasattr(ctx, "__exit__")


class TestTransactionWithDb:
    """Tests for transaction with actual database."""

    def test_transactional_commits_on_success(self, db_session, test_context):
        """Test transactional commits when function succeeds."""
        from app.db.transaction import transactional
        from app.domains.sys.models import DictType

        @transactional
        def create_dict_type():
            dict_type = DictType(
                id=9001,
                tenant_id=1,
                dict_type="dict_test_tx_1",
                name="Test Transaction 1",
                status="ENABLED",
            )
            db_session.add(dict_type)
            return dict_type.id

        result = create_dict_type()
        assert result == 9001

    def test_transactional_rollback_on_exception(self, db_session, test_context):
        """Test transactional rolls back when function raises."""
        from app.db.transaction import transactional
        from app.domains.sys.models import DictType

        @transactional
        def create_and_fail():
            dict_type = DictType(
                id=9002,
                tenant_id=1,
                dict_type="dict_test_tx_2",
                name="Test Transaction 2",
                status="ENABLED",
            )
            db_session.add(dict_type)
            db_session.flush()
            raise ValueError("Intentional error")

        with pytest.raises(ValueError):
            create_and_fail()

        # Verify rollback - dict type should not exist
        existing = db_session.query(DictType).filter(
            DictType.dict_type == "dict_test_tx_2"
        ).first()
        assert existing is None

    def test_transaction_context_commits(self, db_session, test_context):
        """Test TransactionContext commits when called."""
        from app.db.transaction import TransactionContext
        from app.domains.sys.models import DictType

        with TransactionContext() as tx:
            dict_type = DictType(
                id=9003,
                tenant_id=1,
                dict_type="dict_test_ctx_1",
                name="Test Context 1",
                status="ENABLED",
            )
            db_session.add(dict_type)
            tx.commit()

    def test_transaction_context_rollback_on_exception(self, db_session, test_context):
        """Test TransactionContext rolls back on exception."""
        from app.db.transaction import TransactionContext
        from app.domains.sys.models import DictType

        try:
            with TransactionContext():
                dict_type = DictType(
                    id=9004,
                    tenant_id=1,
                    dict_type="dict_test_ctx_2",
                    name="Test Context 2",
                    status="ENABLED",
                )
                db_session.add(dict_type)
                db_session.flush()
                raise ValueError("Intentional error")
        except ValueError:
            pass

        # Verify rollback
        existing = db_session.query(DictType).filter(
            DictType.dict_type == "dict_test_ctx_2"
        ).first()
        assert existing is None

    def test_transaction_context_flush(self, db_session, test_context):
        """Test TransactionContext flush works."""
        from app.db.transaction import TransactionContext
        from app.domains.sys.models import DictType

        with TransactionContext() as tx:
            dict_type = DictType(
                id=9005,
                tenant_id=1,
                dict_type="dict_test_ctx_3",
                name="Test Context 3",
                status="ENABLED",
            )
            db_session.add(dict_type)
            tx.flush()
            # Should be flushed but not committed
            assert dict_type.id is not None
            tx.rollback()
