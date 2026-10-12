# tests/unit/test_pagination.py - Pagination tests (FP-A03)
"""
Tests for pagination and sorting.

Covers:
- UT-A03-01: Default pagination 1/10
- UT-A03-02: Invalid pagination params return 1001
- UT-A03-03: Page beyond data returns empty list
- UT-A03-04: Sort by whitelist field works
- UT-A03-05: Sort by non-whitelist field returns 1001
- UT-A03-06: SQL injection in sort field rejected
"""

import pytest
from unittest.mock import MagicMock

from app.core.errors import BizError
from app.core.pagination import PageParam, PageResult


class TestPageParam:
    """Tests for pagination parameter validation (FP-A03-01)."""
    
    def test_default_page_no_is_1(self):
        """UT-A03-01: Default pageNo is 1."""
        params = PageParam()
        assert params.page_no == 1
    
    def test_default_page_size_is_10(self):
        """UT-A03-01: Default pageSize is 10."""
        params = PageParam()
        assert params.page_size == 10
    
    def test_page_size_max_100(self):
        """UT-A03-02: pageSize > 100 raises error."""
        with pytest.raises(BizError) as exc_info:
            PageParam(page_size=101)
        assert exc_info.value.code == 1001
    
    def test_page_size_min_1(self):
        """UT-A03-02: pageSize < 1 raises error."""
        with pytest.raises(BizError) as exc_info:
            PageParam(page_size=0)
        assert exc_info.value.code == 1001
    
    def test_page_no_min_1(self):
        """UT-A03-02: pageNo < 1 raises error."""
        with pytest.raises(BizError) as exc_info:
            PageParam(page_no=0)
        assert exc_info.value.code == 1001
    
    def test_valid_page_size(self):
        """UT-A03-01: Valid page size accepted."""
        params = PageParam(page_size=50)
        assert params.page_size == 50
    
    def test_valid_page_no(self):
        """UT-A03-01: Valid page number accepted."""
        params = PageParam(page_no=5)
        assert params.page_no == 5
    
    def test_offset_calculation(self):
        """Test offset is calculated correctly."""
        params = PageParam(page_no=3, page_size=20)
        assert params.offset == 40  # (3-1) * 20
    
    def test_limit_equals_page_size(self):
        """Test limit equals page size."""
        params = PageParam(page_size=25)
        assert params.limit == 25


class TestSortValidation:
    """Tests for sort field validation (FP-A03-02)."""
    
    def test_sort_whitelist_field_valid(self):
        """UT-A03-04: Sort by whitelist field succeeds."""
        params = PageParam(sort_field="amount")
        allowed = {"createTime", "amount", "name"}
        
        # Should not raise
        params.validate_sort_field(allowed)
    
    def test_sort_non_whitelist_field_raises_1001(self):
        """UT-A03-05: Sort by non-whitelist field raises 1001."""
        params = PageParam(sort_field="password")
        allowed = {"createTime", "amount"}
        
        with pytest.raises(BizError) as exc_info:
            params.validate_sort_field(allowed)
        
        assert exc_info.value.code == 1001
    
    def test_sort_sql_injection_rejected(self):
        """UT-A03-06: SQL injection in sort field rejected."""
        allowed = {"createTime", "amount"}
        
        malicious_inputs = [
            "amount;drop table x",
            "amount--",
            "amount' OR '1'='1",
            "amount; DELETE FROM users",
            "1=1",
        ]
        
        for malicious in malicious_inputs:
            params = PageParam(sort_field=malicious)
            with pytest.raises(BizError) as exc_info:
                params.validate_sort_field(allowed)
            
            assert exc_info.value.code == 1001
    
    def test_sort_order_valid_values(self):
        """UT-A03-04: Valid sort orders are asc and desc."""
        params_asc = PageParam(sort_order="asc")
        params_desc = PageParam(sort_order="desc")
        
        assert params_asc.sort_order == "asc"
        assert params_desc.sort_order == "desc"
    
    def test_get_order_by_with_mapping(self):
        """Test get_order_by with field mapping."""
        params = PageParam(sort_field="createTime", sort_order="asc")
        mapping = {"createTime": "create_time", "amount": "amount"}
        
        result = params.get_order_by(mapping)
        
        assert result == [("create_time", "asc")]
    
    def test_get_order_by_default(self):
        """Test get_order_by returns default when no sort specified."""
        params = PageParam()
        mapping = {"createTime": "create_time"}
        
        result = params.get_order_by(mapping)
        
        assert result == [("create_time", "desc"), ("id", "desc")]


class TestPageResult:
    """Tests for pagination result structure."""
    
    def test_pagination_result_structure(self):
        """UT-A03-01: Pagination result has correct structure."""
        result = PageResult(
            list=[{"id": "1"}, {"id": "2"}],
            total=25,
            page_no=1,
            page_size=10
        )
        
        assert result.list is not None
        assert len(result.list) == 2
        assert result.total == 25
        assert result.page_no == 1
        assert result.page_size == 10
    
    def test_pagination_beyond_data(self):
        """UT-A03-03: Page beyond data returns empty list with correct total."""
        result = PageResult(
            list=[],
            total=25,
            page_no=10,  # Beyond the data
            page_size=10
        )
        
        assert result.list == []
        assert result.total == 25
    
    def test_has_more(self):
        """Test has_more property."""
        result1 = PageResult(list=[1, 2], total=25, page_no=1, page_size=10)
        result2 = PageResult(list=[1, 2], total=25, page_no=3, page_size=10)
        
        assert result1.has_more is True
        assert result2.has_more is False
    
    def test_total_pages(self):
        """Test total_pages calculation."""
        result = PageResult(list=[], total=25, page_no=1, page_size=10)
        
        assert result.total_pages == 3
    
    def test_empty_result(self):
        """Test empty result factory."""
        params = PageParam(page_no=1, page_size=20)
        result = PageResult.empty(params)
        
        assert result.list == []
        assert result.total == 0
        assert result.page_no == 1
        assert result.page_size == 20
