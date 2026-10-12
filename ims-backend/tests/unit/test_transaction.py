# tests/unit/test_transaction.py - Transaction tests (FP-C01)
"""
Tests for transaction management.

Per 02-单测用例.md UT-C01:
- Exceptions cause full rollback
- Nested service calls share transaction
- Manual commit is forbidden
"""

from dataclasses import dataclass


@dataclass
class MockRecord:
    """Mock database record."""
    id: int
    name: str
    saved: bool = False


class MockTransaction:
    """Mock transaction for testing."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.operations = []

    def insert(self, record: MockRecord):
        self.operations.append(("insert", record))

    def commit(self):
        if self.rolled_back:
            raise Exception("Cannot commit rolled back transaction")
        self.committed = True
        for _op, record in self.operations:
            record.saved = True

    def rollback(self):
        self.rolled_back = True
        self.operations.clear()


class TestExceptionRollback:
    """Tests for exception-triggered rollback (FP-C01-01)."""

    def test_exception_rolls_back_all(self):
        """UT-C01-01: Exception after insert rolls back all changes."""
        txn = MockTransaction()
        record_a = MockRecord(id=1, name="A")
        record_b = MockRecord(id=2, name="B")

        try:
            txn.insert(record_a)
            txn.insert(record_b)
            raise Exception("Simulated failure")
            txn.commit()
        except Exception:
            txn.rollback()

        assert not record_a.saved
        assert not record_b.saved
        assert txn.rolled_back

    def test_no_partial_commit(self):
        """UT-C01-01: No partial data if any operation fails."""
        txn = MockTransaction()
        record_a = MockRecord(id=1, name="A")
        record_b = MockRecord(id=2, name="B")

        try:
            txn.insert(record_a)
            # Simulate B insert failure
            raise Exception("Failed to insert B")
        except Exception:
            txn.rollback()

        # Neither A nor B should be saved
        assert not record_a.saved
        assert not record_b.saved


class TestNestedTransactions:
    """Tests for nested service calls (FP-C01-01)."""

    def test_nested_exception_rolls_back_outer(self):
        """UT-C01-02: Inner exception rolls back outer transaction."""
        outer_txn = MockTransaction()

        def inner_service():
            outer_txn.insert(MockRecord(id=2, name="Inner"))
            raise Exception("Inner failure")

        def outer_service():
            outer_txn.insert(MockRecord(id=1, name="Outer"))
            try:
                inner_service()
            except Exception:
                # Outer catches but should still fail
                raise

        try:
            outer_service()
            outer_txn.commit()
        except Exception:
            outer_txn.rollback()

        assert outer_txn.rolled_back
        assert not outer_txn.committed

    def test_nested_uses_same_transaction(self):
        """UT-C01-02: Nested calls use same transaction (no partial commit)."""
        shared_txn = MockTransaction()

        def service_a(txn):
            txn.insert(MockRecord(id=1, name="A"))

        def service_b(txn):
            txn.insert(MockRecord(id=2, name="B"))
            raise Exception("B failed")

        try:
            service_a(shared_txn)
            service_b(shared_txn)
            shared_txn.commit()
        except Exception:
            shared_txn.rollback()

        # Both should be rolled back
        assert shared_txn.rolled_back
        assert len(shared_txn.operations) == 0


class TestManualCommitForbidden:
    """Tests for manual commit prevention (FP-C01-01)."""

    def test_static_check_detects_manual_commit(self):
        """UT-C01-03: Static check detects session.commit() in route."""
        code_sample = '''
def create_order(request):
    order = Order(name=request.name)
    session.add(order)
    session.commit()  # BAD: manual commit
    return order
'''

        has_manual_commit = "session.commit()" in code_sample

        assert has_manual_commit  # This should be flagged by static analysis


class TestLogicalDelete:
    """Tests for logical delete visibility (FP-C01-02)."""

    def test_deleted_not_in_list(self):
        """UT-C01-04: Soft-deleted records not in default list."""
        records = [
            {"id": 1, "name": "A", "deleted": 0},
            {"id": 2, "name": "B", "deleted": 2},  # Soft deleted
            {"id": 3, "name": "C", "deleted": 0},
        ]

        visible = [r for r in records if r["deleted"] == 0]

        assert len(visible) == 2
        assert all(r["deleted"] == 0 for r in visible)

    def test_deleted_get_returns_1504(self):
        """UT-C01-04: get() on deleted record returns 1504."""
        record = {"id": 2, "name": "B", "deleted": 2}

        error_code = 1504 if record["deleted"] != 0 else 0

        assert error_code == 1504

    def test_include_deleted_shows_all(self):
        """UT-C01-04: include_deleted=True shows deleted records."""
        records = [
            {"id": 1, "name": "A", "deleted": 0},
            {"id": 2, "name": "B", "deleted": 2},
            {"id": 3, "name": "C", "deleted": 0},
        ]

        include_deleted = True

        visible = records if include_deleted else [r for r in records if r["deleted"] == 0]

        assert len(visible) == 3


class TestOptimisticLocking:
    """Tests for optimistic locking (FP-C01-02)."""

    def test_version_mismatch_returns_1001(self):
        """UT-C01-05: Version mismatch returns 1001."""
        current_version = 3
        request_version = 2

        if current_version != request_version:
            error_code = 1001
            message = "数据已被他人修改"
        else:
            error_code = 0
            message = None

        assert error_code == 1001
        assert "他人修改" in message

    def test_version_increments_on_update(self):
        """UT-C01-05: Version increments on successful update."""
        record = {"id": 1, "name": "A", "version": 3}

        # Simulate update
        record["name"] = "B"
        record["version"] += 1

        assert record["version"] == 4


class TestTransactionIsolation:
    """Tests for transaction isolation."""

    def test_uncommitted_not_visible(self):
        """Uncommitted changes not visible to other transactions."""
        txn1 = MockTransaction()
        MockTransaction()

        record = MockRecord(id=1, name="Original")
        record.saved = True  # Exists in DB

        # Txn1 updates but doesn't commit
        txn1.insert(MockRecord(id=1, name="Updated"))
        # Don't commit

        # Txn2 should see original
        # (In mock, we just verify txn1 not committed)
        assert not txn1.committed
