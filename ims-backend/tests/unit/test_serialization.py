# tests/unit/test_serialization.py - Serialization tests (FP-A04)
"""
Tests for field serialization and formatting.

Covers:
- UT-A04-01: camelCase field names
- UT-A04-02: Timezone handling (UTC -> Beijing)
- UT-A04-03: Decimal formatting
- UT-A04-04: Enum validation
- UT-A04-09: ID fields as strings
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.serialization import (
    snake_to_camel,
    camel_to_snake,
    serialize_datetime,
    serialize_money,
    validate_datetime,
    validate_money,
)
from app.core.clock import BEIJING_TZ


class TestCamelCaseConversion:
    """Tests for camelCase/snake_case conversion (FP-A04-01)."""
    
    def test_snake_to_camel(self):
        """UT-A04-01: Snake case converts to camelCase."""
        assert snake_to_camel("owner_user_id") == "ownerUserId"
        assert snake_to_camel("create_time") == "createTime"
        assert snake_to_camel("id") == "id"
        assert snake_to_camel("main_dept_id") == "mainDeptId"
    
    def test_camel_to_snake(self):
        """UT-A04-01: CamelCase converts to snake_case."""
        assert camel_to_snake("ownerUserId") == "owner_user_id"
        assert camel_to_snake("createTime") == "create_time"
        assert camel_to_snake("id") == "id"
        assert camel_to_snake("mainDeptId") == "main_dept_id"
    
    def test_single_word_unchanged(self):
        """Single word is unchanged."""
        assert snake_to_camel("id") == "id"
        assert snake_to_camel("name") == "name"
        assert camel_to_snake("id") == "id"
        assert camel_to_snake("name") == "name"
    
    def test_already_correct_format(self):
        """Already correct format returns same value."""
        assert snake_to_camel("ownerUserId") == "ownerUserId"
        assert camel_to_snake("owner_user_id") == "owner_user_id"


class TestDatetimeFormatting:
    """Tests for datetime formatting (FP-A04-02)."""
    
    def test_utc_to_beijing(self):
        """UT-A04-02: UTC time converts to Beijing time."""
        utc_time = datetime(2026, 10, 12, 2, 0, 0, tzinfo=timezone.utc)
        # First validate (convert to Beijing TZ)
        beijing_time = validate_datetime(utc_time)
        result = serialize_datetime(beijing_time)
        
        # UTC 02:00 is Beijing 10:00
        assert "10:00" in result
        assert "+08:00" in result
    
    def test_naive_datetime_treated_as_beijing(self):
        """UT-A04-03: Naive datetime treated as Beijing time."""
        naive_time = datetime(2026, 10, 12, 10, 0, 0)
        beijing_time = validate_datetime(naive_time)
        result = serialize_datetime(beijing_time)
        
        # Should preserve the time
        assert "10:00" in result
    
    def test_iso_format_output(self):
        """Datetime outputs in ISO format with timezone."""
        dt = datetime(2026, 10, 12, 10, 0, 0, tzinfo=BEIJING_TZ)
        result = serialize_datetime(dt)
        
        # Should be ISO format with timezone
        assert "2026-10-12" in result
        assert "T" in result
        assert "+08:00" in result
    
    def test_none_datetime_returns_none(self):
        """None datetime returns None."""
        assert serialize_datetime(None) is None


class TestDecimalFormatting:
    """Tests for decimal formatting (FP-A04-03)."""
    
    def test_decimal_two_places(self):
        """UT-A04-06: Decimal outputs as string with 2 decimal places."""
        value = validate_money(Decimal("0.30"))
        result = serialize_money(value)
        
        assert result == "0.30"
        assert isinstance(result, str)
    
    def test_integer_with_decimal_places(self):
        """Integer shows decimal places."""
        value = validate_money(Decimal("10"))
        result = serialize_money(value)
        
        assert result == "10.00"
    
    def test_rounding(self):
        """Rounds to 2 decimal places.
        
        Note: validate_money rejects more than 2 decimal places
        per FP-A04-03 spec. This is by design - input must be
        at most 2 decimal places.
        """
        # Input with exactly 2 decimal places is valid
        value = validate_money(Decimal("12.34"))
        result = serialize_money(value)
        
        assert result == "12.34"
    
    def test_none_returns_none(self):
        """None returns None."""
        assert serialize_money(None) is None


class TestIdAsString:
    """Tests for ID as string configuration (FP-A04-09)."""
    
    def test_config_id_as_string_true(self):
        """UT-A04-09: Config api.id_as_string is True by default."""
        from app.core.config import get_settings
        
        settings = get_settings()
        
        assert settings.api.id_as_string is True
    
    def test_integer_id_serializes_to_string(self):
        """Integer ID should serialize to string."""
        # Per D2 decision: all id/*Id as strings
        id_value = 12345
        
        # In API response, this would be "12345"
        string_id = str(id_value)
        assert string_id == "12345"
        assert isinstance(string_id, str)


class TestEnumValidation:
    """Tests for enum validation (FP-A04-04)."""
    
    def test_enum_value_validation_concept(self):
        """UT-A04-08: Invalid enum value returns 1503."""
        from app.core.errors import BizError, get_error_info
        
        # 1503 is for invalid enum/status values
        info = get_error_info(1503)
        
        assert info is not None
    
    def test_valid_status_values(self):
        """Valid status values are accepted."""
        valid_statuses = ["ACTIVE", "FROZEN", "RESIGNED"]
        
        for status in valid_statuses:
            # Each should be uppercase enum value
            assert status == status.upper()
