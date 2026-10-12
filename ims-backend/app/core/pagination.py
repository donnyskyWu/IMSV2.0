# app/core/pagination.py - Pagination utilities (FP-A03-01, FP-A03-02)
"""
Unified pagination parameter and result handling.

Rules per FP-A03-01:
- pageNo: >= 1, default 1
- pageSize: 1-100, default 10
- pageNo < 1, pageSize < 1 or > 100, non-integer -> 1001
- total: count after data scope filtering

Rules per FP-A03-02:
- sortField: camelCase, must be in whitelist
- sortOrder: asc/desc, default desc
- Field not in whitelist -> 1001 with fieldErrors pointing to sortField
- Sort values never concatenated into SQL strings
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

from app.core.errors import BizError, FieldError

T = TypeVar("T")

# Default values per spec
DEFAULT_PAGE_NO = 1
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


class PageParam(BaseModel):
    """Pagination parameters."""

    page_no: int = Field(default=DEFAULT_PAGE_NO, alias="pageNo", ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, alias="pageSize", ge=1, le=MAX_PAGE_SIZE)
    sort_field: Optional[str] = Field(default=None, alias="sortField")
    sort_order: str = Field(default="desc", alias="sortOrder", pattern="^(asc|desc)$")

    model_config = {"populate_by_name": True}

    @field_validator("page_no", mode="before")
    @classmethod
    def validate_page_no(cls, v: Any) -> int:
        if v is None:
            return DEFAULT_PAGE_NO
        try:
            val = int(v)
            if val < 1:
                raise BizError.validation_error([
                    FieldError("pageNo", "页码必须大于等于1").to_dict()
                ])
            return val
        except (TypeError, ValueError) as err:
            raise BizError.validation_error([
                FieldError("pageNo", "页码必须为整数").to_dict()
            ]) from err

    @field_validator("page_size", mode="before")
    @classmethod
    def validate_page_size(cls, v: Any) -> int:
        if v is None:
            return DEFAULT_PAGE_SIZE
        try:
            val = int(v)
            if val < 1:
                raise BizError.validation_error([
                    FieldError("pageSize", "每页条数必须大于等于1").to_dict()
                ])
            if val > MAX_PAGE_SIZE:
                # Per spec: reject rather than truncate
                raise BizError.validation_error([
                    FieldError("pageSize", f"每页条数不能超过{MAX_PAGE_SIZE}").to_dict()
                ])
            return val
        except (TypeError, ValueError) as err:
            raise BizError.validation_error([
                FieldError("pageSize", "每页条数必须为整数").to_dict()
            ]) from err

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page_no - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size

    def validate_sort_field(self, allowed_fields: set[str]) -> None:
        """
        Validate sort field against whitelist.

        Args:
            allowed_fields: Set of allowed field names (camelCase)

        Raises:
            BizError: 1001 if field not in whitelist
        """
        if self.sort_field and self.sort_field not in allowed_fields:
            raise BizError.validation_error([
                FieldError("sortField", "不支持按该字段排序").to_dict()
            ])

    def get_order_by(
        self,
        field_mapping: dict[str, str],
        default_order: Optional[list[tuple[str, str]]] = None
    ) -> list[tuple[str, str]]:
        """
        Get order by clauses with snake_case column names.

        Args:
            field_mapping: camelCase -> snake_case mapping
            default_order: Default order if no sort specified

        Returns:
            List of (column_name, order) tuples
        """
        if not self.sort_field:
            return default_order or [("create_time", "desc"), ("id", "desc")]

        if self.sort_field not in field_mapping:
            raise BizError.validation_error([
                FieldError("sortField", "不支持按该字段排序").to_dict()
            ])

        return [(field_mapping[self.sort_field], self.sort_order)]


class PageResult(BaseModel, Generic[T]):
    """Paginated result."""

    list: List[T] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page_no: int = Field(default=DEFAULT_PAGE_NO, alias="pageNo", ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, alias="pageSize", ge=1)

    model_config = {"populate_by_name": True}

    @classmethod
    def empty(cls, page_param: PageParam) -> "PageResult[T]":
        """Create empty result."""
        return cls(
            list=[],
            total=0,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    @classmethod
    def of(
        cls,
        items: list[T],
        total: int,
        page_param: PageParam,
    ) -> "PageResult[T]":
        """Create result from items and total count."""
        return cls(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    @property
    def has_more(self) -> bool:
        """Check if there are more pages."""
        return self.page_no * self.page_size < self.total

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
