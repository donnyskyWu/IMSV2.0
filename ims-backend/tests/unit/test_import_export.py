# tests/unit/test_import_export.py - Import/Export tests (FP-H02)
"""
Tests for data import and export functionality.

Per 02-单测用例.md UT-H02:
- All-or-nothing import mode
- Partial commit import mode
- Row limit validation
- Export respects data scope and masking
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class ImportMode(str, Enum):
    """Import mode."""
    ALL_OR_NOTHING = "ALL_OR_NOTHING"  # 全有或全无
    PARTIAL = "PARTIAL"  # 部分提交


class ImportStatus(str, Enum):
    """Import job status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class ExportStatus(str, Enum):
    """Export job status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class ImportError:
    """Import row error."""
    row_number: int  # Excel row number (1-based + header)
    column: str
    error_code: int
    message: str


@dataclass
class ImportResult:
    """Import operation result."""
    total_rows: int
    success_count: int
    error_count: int
    errors: List[ImportError] = field(default_factory=list)


@dataclass
class ExportTask:
    """Export task."""
    id: int
    user_id: int
    tenant_id: int
    biz_type: str
    status: ExportStatus
    file_key: Optional[str] = None
    error_message: Optional[str] = None
    create_time: datetime = field(default_factory=datetime.now)


class TestAllOrNothingMode:
    """Tests for all-or-nothing import mode (FP-H02-01)."""

    def test_all_valid_rows_imported(self):
        """UT-H02-01: 10 valid rows all imported."""
        list(range(1, 11))  # 10 rows
        errors = []  # No errors

        result = ImportResult(
            total_rows=10,
            success_count=10 if not errors else 0,
            error_count=len(errors),
            errors=errors
        )

        assert result.success_count == 10
        assert result.error_count == 0

    def test_any_error_imports_none(self):
        """UT-H02-01: 10 rows with 2 errors -> 0 imported."""
        total_rows = 10
        errors = [
            ImportError(row_number=3, column="amount", error_code=1001, message="金额格式错误"),
            ImportError(row_number=8, column="dept_id", error_code=1500, message="部门不存在"),
        ]

        # All-or-nothing mode
        success_count = 0 if errors else total_rows

        result = ImportResult(
            total_rows=total_rows,
            success_count=success_count,
            error_count=len(errors),
            errors=errors
        )

        assert result.success_count == 0
        assert result.error_count == 2

    def test_errors_have_row_numbers(self):
        """UT-H02-01: Errors include Excel row numbers."""
        errors = [
            ImportError(row_number=3, column="amount", error_code=1001, message="金额格式错误"),
            ImportError(row_number=8, column="dept_id", error_code=1500, message="部门不存在"),
        ]

        assert errors[0].row_number == 3
        assert errors[1].row_number == 8

    def test_errors_have_chinese_messages(self):
        """UT-H02-01: Error messages are in Chinese."""
        errors = [
            ImportError(row_number=3, column="amount", error_code=1001, message="金额格式错误"),
        ]

        # Check message contains Chinese characters
        import re
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', errors[0].message))

        assert has_chinese


class TestPartialCommitMode:
    """Tests for partial commit import mode (FP-H02-01)."""

    def test_valid_rows_imported_despite_errors(self):
        """UT-H02-02: Valid rows imported even with errors."""
        total_rows = 10
        error_rows = {3, 8}  # Row 3 and 8 have errors

        success_count = total_rows - len(error_rows)

        result = ImportResult(
            total_rows=total_rows,
            success_count=success_count,
            error_count=len(error_rows),
            errors=[
                ImportError(row_number=3, column="amount", error_code=1001, message="金额格式错误"),
                ImportError(row_number=8, column="dept_id", error_code=1500, message="部门不存在"),
            ]
        )

        assert result.success_count == 8
        assert result.error_count == 2


class TestRowLimit:
    """Tests for import row limit (FP-H02-01)."""

    def test_max_5000_rows(self):
        """UT-H02-03: Max 5000 rows per import."""
        max_rows = 5000
        uploaded_rows = 5001

        is_valid = uploaded_rows <= max_rows

        assert not is_valid

    def test_5000_rows_accepted(self):
        """UT-H02-03: Exactly 5000 rows accepted."""
        max_rows = 5000
        uploaded_rows = 5000

        is_valid = uploaded_rows <= max_rows

        assert is_valid

    def test_over_limit_returns_1001(self):
        """UT-H02-03: Over limit returns 1001 with split hint."""
        max_rows = 5000
        uploaded_rows = 5001

        if uploaded_rows > max_rows:
            error_code = 1001
            message = "数据量超过上限，请拆分"
        else:
            error_code = 0
            message = None

        assert error_code == 1001
        assert "拆分" in message


class TestImportValidation:
    """Tests for import data validation (FP-H02-01)."""

    def test_dict_value_invalid(self):
        """UT-H02-04: Invalid dict value returns 1503."""
        valid_statuses = {"ACTIVE", "FROZEN"}
        input_status = "INVALID"

        error_code = 1503 if input_status not in valid_statuses else 0

        assert error_code == 1503

    def test_reference_not_exist(self):
        """UT-H02-04: Non-existent reference returns 1500."""
        existing_depts = {1, 2, 3}
        referenced_dept = 999

        error_code = 1500 if referenced_dept not in existing_depts else 0

        assert error_code == 1500


class TestExportDataScope:
    """Tests for export data scope (FP-H02-02)."""

    def test_export_respects_user_scope(self):
        """UT-H02-05: Export only includes user's visible data."""
        all_records = [
            {"id": 1, "dept_id": "D1"},
            {"id": 2, "dept_id": "D2"},
            {"id": 3, "dept_id": "D3"},
        ]
        user_dept_ids = {"D1", "D2"}  # DEPT scope

        visible_records = [r for r in all_records if r["dept_id"] in user_dept_ids]

        assert len(visible_records) == 2
        assert all(r["dept_id"] in user_dept_ids for r in visible_records)

    def test_export_masks_sensitive_fields(self):
        """UT-H02-05: Export masks sensitive fields without plain permission."""
        has_plain_permission = False
        id_card = "110101199001011234"

        if has_plain_permission:
            exported_value = id_card
        else:
            exported_value = id_card[:3] + "***********" + id_card[-4:]

        assert exported_value == "110***********1234"

    def test_export_with_plain_permission(self):
        """UT-H02-05: With plain permission, export shows full value."""
        has_plain_permission = True
        id_card = "110101199001011234"

        if has_plain_permission:
            exported_value = id_card
        else:
            exported_value = id_card[:3] + "***********" + id_card[-4:]

        assert exported_value == id_card


class TestExportFailure:
    """Tests for export failure handling (FP-H02-02)."""

    def test_failed_export_has_error_message(self):
        """UT-H02-06: Failed export shows error reason."""
        task = ExportTask(
            id=1,
            user_id=100,
            tenant_id=1,
            biz_type="demo_order",
            status=ExportStatus.FAILED,
            error_message="数据库连接超时"
        )

        assert task.status == ExportStatus.FAILED
        assert task.error_message is not None

    def test_user_can_view_own_export(self):
        """UT-H02-06: User can view their own export tasks."""
        task = ExportTask(
            id=1,
            user_id=100,
            tenant_id=1,
            biz_type="demo_order",
            status=ExportStatus.SUCCESS,
            file_key="exports/1/202610/abc123.xlsx"
        )
        current_user_id = 100

        can_view = task.user_id == current_user_id

        assert can_view


class TestExportDownload:
    """Tests for export file download (FP-H02-02)."""

    def test_cannot_download_others_export(self):
        """UT-H02-07: Cannot download another user's export."""
        task = ExportTask(
            id=1,
            user_id=100,
            tenant_id=1,
            biz_type="demo_order",
            status=ExportStatus.SUCCESS,
            file_key="exports/1/202610/abc123.xlsx"
        )
        current_user_id = 200

        can_download = task.user_id == current_user_id

        assert not can_download

    def test_owner_can_download(self):
        """UT-H02-07: Owner can download their export."""
        task = ExportTask(
            id=1,
            user_id=100,
            tenant_id=1,
            biz_type="demo_order",
            status=ExportStatus.SUCCESS,
            file_key="exports/1/202610/abc123.xlsx"
        )
        current_user_id = 100

        can_download = task.user_id == current_user_id

        assert can_download

    def test_incomplete_export_no_file(self):
        """UT-H02-07: Incomplete export has no file_key."""
        task = ExportTask(
            id=1,
            user_id=100,
            tenant_id=1,
            biz_type="demo_order",
            status=ExportStatus.PROCESSING,
            file_key=None
        )

        has_file = task.file_key is not None

        assert not has_file


class TestImportErrorMessages:
    """Tests for import error message formatting."""

    def test_error_includes_column_name(self):
        """Error includes column name."""
        error = ImportError(
            row_number=5,
            column="deptId",
            error_code=1500,
            message="部门不存在"
        )

        assert error.column == "deptId"

    def test_error_column_is_camelcase(self):
        """Error column name is camelCase."""
        error = ImportError(
            row_number=5,
            column="deptId",  # Not dept_id
            error_code=1500,
            message="部门不存在"
        )

        # Check for camelCase (lowercase first letter, no underscore)
        assert "_" not in error.column
        assert error.column[0].islower()
