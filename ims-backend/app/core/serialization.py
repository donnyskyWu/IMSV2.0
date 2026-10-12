# app/core/serialization.py - Serialization utilities (FP-A04-01 ~ FP-A04-04)
"""
Serialization conventions:
- FP-A04-01: camelCase JSON <-> snake_case DB
- FP-A04-02: DateTime as ISO 8601 with +08:00, dates as yyyy-MM-dd
- FP-A04-03: Money as string with 2 decimals, Percent as % value (interface) <-> decimal (DB)
- FP-A04-04: Enums as string canonical values, id/*Id as strings when api.id_as_string=true

D2 decision: All id/*Id always output as strings, no off switch.
"""

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated, Any, Optional

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
    field_serializer,
    model_validator,
)
from pydantic.alias_generators import to_camel

from app.core.clock import BEIJING_TZ, format_datetime, parse_datetime


def to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    return re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")


class BaseSchema(BaseModel):
    """
    Base schema with camelCase serialization.

    All schemas should inherit from this to ensure consistent
    camelCase <-> snake_case conversion.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )


class IdMixin:
    """
    Mixin for models with id field.

    Ensures id is serialized as string per D2 decision.
    """

    @field_serializer("id", check_fields=False)
    @classmethod
    def serialize_id(cls, v: Any) -> str:
        """Serialize id as string."""
        if v is None:
            return ""
        return str(v)


def serialize_id_field(v: Any) -> str:
    """Serialize any *Id field as string."""
    if v is None:
        return ""
    return str(v)


def validate_datetime(v: Any) -> Optional[datetime]:
    """
    Validate and normalize datetime input.

    Accepts:
    - datetime objects
    - ISO 8601 strings with or without timezone
    - Strings without timezone are treated as Beijing time
    """
    if v is None:
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=BEIJING_TZ)
        else:
            return v.astimezone(BEIJING_TZ)
    if isinstance(v, str):
        return parse_datetime(v)
    raise ValueError(f"Invalid datetime value: {v}")


def serialize_datetime(v: Optional[datetime]) -> Optional[str]:
    """Serialize datetime as ISO 8601 with Beijing timezone."""
    if v is None:
        return None
    return format_datetime(v)


def validate_date(v: Any) -> Optional[date]:
    """Validate date input (yyyy-MM-dd format)."""
    if v is None:
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        # Only accept yyyy-MM-dd format
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("日期格式应为 yyyy-MM-dd")
        try:
            return date.fromisoformat(v)
        except ValueError as err:
            raise ValueError("日期格式应为 yyyy-MM-dd") from err
    raise ValueError(f"Invalid date value: {v}")


def serialize_date(v: Optional[date]) -> Optional[str]:
    """Serialize date as yyyy-MM-dd."""
    if v is None:
        return None
    return v.isoformat()


def validate_money(v: Any) -> Optional[Decimal]:
    """
    Validate money input.

    Accepts number or string, max 2 decimal places.
    """
    if v is None:
        return None
    try:
        d = v if isinstance(v, Decimal) else Decimal(str(v))

        # Check decimal places
        if d.as_tuple().exponent is not None and abs(d.as_tuple().exponent) > 2:
            raise ValueError("金额最多保留2位小数")

        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as err:
        raise ValueError("金额格式不正确") from err


def serialize_money(v: Optional[Decimal]) -> Optional[str]:
    """Serialize money as string with 2 decimal places."""
    if v is None:
        return None
    return f"{v:.2f}"


def validate_percent(v: Any) -> Optional[Decimal]:
    """
    Validate percent input (interface value -> DB value).

    Interface: 5 (meaning 5%)
    DB: 0.0500 (DECIMAL(6,4))
    """
    if v is None:
        return None
    try:
        d = v if isinstance(v, Decimal) else Decimal(str(v))

        # Convert from percentage to decimal
        return (d / 100).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except InvalidOperation as err:
        raise ValueError("百分比格式不正确") from err


def serialize_percent(v: Optional[Decimal]) -> Optional[float]:
    """
    Serialize percent (DB value -> interface value).

    DB: 0.0500
    Interface: 5 (number)
    """
    if v is None:
        return None
    return float(v * 100)


# Annotated types for Pydantic
DateTimeField = Annotated[
    Optional[datetime],
    BeforeValidator(validate_datetime),
    PlainSerializer(serialize_datetime, when_used="always"),
]

DateField = Annotated[
    Optional[date],
    BeforeValidator(validate_date),
    PlainSerializer(serialize_date, when_used="always"),
]

Money = Annotated[
    Optional[Decimal],
    BeforeValidator(validate_money),
    PlainSerializer(serialize_money, when_used="always"),
]

Percent = Annotated[
    Optional[Decimal],
    BeforeValidator(validate_percent),
    PlainSerializer(serialize_percent, when_used="always"),
]

IdStr = Annotated[
    Any,
    PlainSerializer(serialize_id_field, when_used="always"),
]


class ResponseSchema(BaseSchema):
    """
    Base schema for API responses with automatic id string conversion.

    All response schemas should inherit from this.
    """

    @model_validator(mode="after")
    def convert_ids_to_strings(self) -> "ResponseSchema":
        """Convert all *Id fields and id field to strings."""
        for field_name, value in self.__dict__.items():
            is_id_field = field_name == "id" or field_name.endswith("_id")
            if value is not None and is_id_field and isinstance(value, int):
                setattr(self, field_name, str(value))
        return self


def snake_to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def camel_to_snake(s: str) -> str:
    """Convert camelCase to snake_case."""
    return re.sub(r"([A-Z])", r"_\1", s).lower().lstrip("_")
