# tests/unit/test_dict_service.py - Dictionary service tests (FP-B07)
"""
Tests for dictionary service.

Covers:
- UT-B07-03-01 through UT-B07-03-05: Dictionary value listing and caching
- UT-B07-01-01 through UT-B07-01-04: Dictionary type/value format validation
- UT-B07-04-01 through UT-B07-04-03: Enum validation against dictionary
"""

import pytest

from app.core.cache import Cache
from app.core.errors import BizError
from app.domains.sys.models import DictData
from app.services.dict import DICT_REF_CHECKS, DictService


class TestDictService:
    """Tests for DictService."""

    @pytest.mark.asyncio
    async def test_get_dict_data_simple_list_returns_enabled_only(
        self, db_session, test_context, sample_dict
    ):
        """UT-B07-03-01: Returns only enabled dictionary values."""
        service = DictService()

        result = await service.get_dict_data_simple_list("dict_user_status")

        assert len(result) == 3
        assert all(item["dict_value"] in sample_dict["values"] for item in result)

    @pytest.mark.asyncio
    async def test_get_dict_data_simple_list_includes_color_type(
        self, db_session, test_context, sample_dict
    ):
        """UT-B07-03-02: Result includes colorType field."""
        service = DictService()

        result = await service.get_dict_data_simple_list("dict_user_status")

        assert all("color_type" in item for item in result)
        active_item = next(i for i in result if i["dict_value"] == "ACTIVE")
        assert active_item["color_type"] == "success"

    @pytest.mark.asyncio
    async def test_get_dict_data_simple_list_sorted_by_sort_field(
        self, db_session, test_context, sample_dict
    ):
        """UT-B07-03-03: Results are sorted by sort field."""
        service = DictService()

        result = await service.get_dict_data_simple_list("dict_user_status")

        sorts = [item["sort"] for item in result]
        assert sorts == sorted(sorts)

    @pytest.mark.asyncio
    async def test_get_dict_data_empty_for_unknown_type(
        self, db_session, test_context
    ):
        """UT-B07-03-04: Returns empty list for unknown dict type."""
        service = DictService()

        result = await service.get_dict_data_simple_list("dict_nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_validate_dict_value_success(
        self, db_session, test_context, sample_dict
    ):
        """UT-B07-01-01: Valid dictionary value passes validation."""
        service = DictService()

        result = await service.validate_dict_value("dict_user_status", "ACTIVE")

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_dict_value_invalid_raises_1503(
        self, db_session, test_context, sample_dict
    ):
        """UT-B07-01-02: Invalid dictionary value raises 1503."""
        service = DictService()

        with pytest.raises(BizError) as exc_info:
            await service.validate_dict_value("dict_user_status", "INVALID")

        assert exc_info.value.code == 1503

    def test_validate_dict_type_format_valid(self):
        """UT-B07-01-03: Valid dict_type format passes."""
        service = DictService()

        # Should not raise
        service.validate_dict_type_format("dict_user_status")
        service.validate_dict_type_format("dict_platform_type")
        service.validate_dict_type_format("dict_a123")

    def test_validate_dict_type_format_invalid_raises_1001(self):
        """UT-B07-01-04: Invalid dict_type format raises 1001."""
        service = DictService()

        invalid_types = [
            "user_status",  # Missing dict_ prefix
            "dict_UserStatus",  # Contains uppercase
            "Dict_status",  # Uppercase prefix
            "dict_",  # Empty after prefix
            "dict_1abc",  # Starts with number after prefix
        ]

        for invalid_type in invalid_types:
            with pytest.raises(BizError) as exc_info:
                service.validate_dict_type_format(invalid_type)
            assert exc_info.value.code == 1001

    def test_validate_dict_value_format_valid(self):
        """UT-B07-04-01: Valid dict_value format passes."""
        service = DictService()

        # Should not raise
        service.validate_dict_value_format("ACTIVE")
        service.validate_dict_value_format("PENDING_REVIEW")
        service.validate_dict_value_format("A123")

    def test_validate_dict_value_format_invalid_raises_1001(self):
        """UT-B07-04-02: Invalid dict_value format raises 1001."""
        service = DictService()

        invalid_values = [
            "active",  # Lowercase
            "Active",  # Mixed case
            "_ACTIVE",  # Starts with underscore
            "123ABC",  # Starts with number
        ]

        for invalid_value in invalid_values:
            with pytest.raises(BizError) as exc_info:
                service.validate_dict_value_format(invalid_value)
            assert exc_info.value.code == 1001

    def test_validate_color_type_valid(self):
        """UT-B07-04-03: Valid color types pass validation."""
        service = DictService()

        valid_colors = [
            "primary", "success", "warning", "danger",
            "neutral", "info", "purple", "yellow"
        ]

        for color in valid_colors:
            # Should not raise
            service.validate_color_type(color)

    def test_validate_color_type_invalid_raises_1001(self):
        """UT-B07-04-04: Invalid color type raises 1001."""
        service = DictService()

        with pytest.raises(BizError) as exc_info:
            service.validate_color_type("red")

        assert exc_info.value.code == 1001

    @pytest.mark.asyncio
    async def test_local_cache_hit_ignores_db_change_within_ttl(
        self, db_session, test_context, sample_dict
    ):
        """60 秒内第二次读取走进程内缓存，不反映刚改过的库内标签。"""
        service = DictService()
        Cache.delete(f"{service.CACHE_PREFIX}dict_user_status")

        first = await service.get_dict_data_simple_list("dict_user_status")
        active = next(item for item in first if item["dict_value"] == "ACTIVE")
        assert active["dict_label"] == "在职"

        row = db_session.query(DictData).filter(
            DictData.dict_type == "dict_user_status",
            DictData.dict_value == "ACTIVE",
            DictData.deleted == 0,
        ).one()
        row.dict_label = "已改"
        db_session.flush()

        second = await service.get_dict_data_simple_list("dict_user_status")
        cached = next(item for item in second if item["dict_value"] == "ACTIVE")
        # 返回的是同一份列表，说明没有回库重查。
        assert second is first
        assert cached["dict_label"] == "在职"
        db_session.refresh(row)
        assert row.dict_label == "已改"

    @pytest.mark.asyncio
    async def test_update_missing_value_raises_1503(
        self, db_session, test_context, sample_dict
    ):
        """改不存在的字典值返回 1503。"""
        service = DictService()

        with pytest.raises(BizError) as exc_info:
            await service.update_dict_label("dict_user_status", "NO_SUCH", "不存在")

        assert exc_info.value.code == 1503

    @pytest.mark.asyncio
    async def test_delete_missing_value_raises_1504(self, db_session, test_context):
        """删不存在的字典值返回 1504。"""
        service = DictService()

        with pytest.raises(BizError) as exc_info:
            await service.delete_dict_value(999_999)

        assert exc_info.value.code == 1504

    @pytest.mark.asyncio
    async def test_delete_continues_when_ref_count_is_zero(
        self, db_session, test_context
    ):
        """引用检查返回 0 时不拦截，软删除把 deleted 写成自身 id。"""
        row = DictData(
            tenant_id=1,
            dict_type="dict_ref_zero",
            dict_value="ZERO",
            dict_label="零引用",
            status="ENABLED",
            is_builtin=False,
        )
        db_session.add(row)
        db_session.flush()

        def zero_refs(_session, data_id):
            assert data_id == row.id
            return 0

        saved = list(DICT_REF_CHECKS)
        DICT_REF_CHECKS.clear()
        DICT_REF_CHECKS.append(zero_refs)
        try:
            await DictService().delete_dict_value(row.id)
        finally:
            DICT_REF_CHECKS.clear()
            DICT_REF_CHECKS.extend(saved)

        db_session.refresh(row)
        assert row.deleted == row.id

    @pytest.mark.asyncio
    async def test_get_dict_label_skips_non_matching_values(
        self, db_session, test_context, sample_dict
    ):
        """标签查找会跳过排在前面的值，命中后面的 FROZEN。"""
        service = DictService()
        Cache.delete(f"{service.CACHE_PREFIX}dict_user_status")

        label = await service.get_dict_label("dict_user_status", "FROZEN")

        assert label == "冻结"
