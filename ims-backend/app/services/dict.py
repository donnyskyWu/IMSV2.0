# app/services/dict.py - Dictionary service (FW-B07)
"""
Dictionary service.

Implements:
- FP-B07-01: Dictionary type and value management
- FP-B07-03: Dictionary caching (Redis + local 60s TTL)
- FP-B07-04: Backend enum validation against dictionary
"""

import json
import re
from typing import Any, Optional

from app.core.cache import Cache
from app.core.errors import BizError
from app.db.session import get_db_session


class DictService:
    """Dictionary management service."""
    
    CACHE_PREFIX = "ims:dict:"
    LOCAL_TTL = 60
    
    # Dictionary value regex: ^[A-Z][A-Z0-9_]*$
    DICT_VALUE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
    # Dictionary type regex: ^dict_[a-z][a-z0-9_]*$
    DICT_TYPE_PATTERN = re.compile(r"^dict_[a-z][a-z0-9_]*$")
    
    # Valid color types
    VALID_COLOR_TYPES = {
        "primary", "success", "warning", "danger", 
        "neutral", "info", "purple", "yellow"
    }
    
    async def get_dict_data_simple_list(
        self, dict_type: str
    ) -> list[dict[str, Any]]:
        """
        Get enabled dictionary values for a type.
        
        Rules per FP-B07-03:
        - Returns enabled values only
        - Includes colorType
        - Cached in Redis (ims:dict:<type>), TTL 60s local cache
        
        Args:
            dict_type: Dictionary type code
            
        Returns:
            List of dict items with dict_value, dict_label, color_type, sort
        """
        cache_key = f"{self.CACHE_PREFIX}{dict_type}"
        
        # Try cache first
        cached = Cache.get_json(cache_key)
        if cached is not None:
            return cached
        
        # Query from database
        from app.domains.sys.models import DictData
        session = get_db_session()
        
        items = session.query(DictData).filter(
            DictData.dict_type == dict_type,
            DictData.status == "ENABLED",
            DictData.deleted == 0,
        ).order_by(DictData.sort).all()
        
        result = [
            {
                "dict_value": item.dict_value,
                "dict_label": item.dict_label,
                "color_type": item.color_type or "neutral",
                "sort": item.sort or 0,
            }
            for item in items
        ]
        
        # Cache for 60 seconds
        Cache.set_json(cache_key, result, ttl=self.LOCAL_TTL)
        
        return result
    
    async def get_dict_type_list(self) -> list[dict[str, Any]]:
        """
        Get all dictionary types.
        
        Returns:
            List of dict types with dict_type, name
        """
        from app.domains.sys.models import DictType
        session = get_db_session()
        
        items = session.query(DictType).filter(
            DictType.status == "ENABLED",
            DictType.deleted == 0,
        ).order_by(DictType.dict_type).all()
        
        return [
            {
                "dict_type": item.dict_type,
                "name": item.name,
            }
            for item in items
        ]
    
    async def validate_dict_value(
        self, dict_type: str, dict_value: str, allow_disabled: bool = False
    ) -> bool:
        """
        Validate a dictionary value exists and is enabled.
        
        Args:
            dict_type: Dictionary type code
            dict_value: Value to validate
            allow_disabled: Whether to allow disabled values
            
        Returns:
            True if valid
            
        Raises:
            BizError(1503): Dictionary value invalid
        """
        from app.domains.sys.models import DictData
        session = get_db_session()
        
        query = session.query(DictData).filter(
            DictData.dict_type == dict_type,
            DictData.dict_value == dict_value,
            DictData.deleted == 0,
        )
        
        if not allow_disabled:
            query = query.filter(DictData.status == "ENABLED")
        
        exists = query.first() is not None
        
        if not exists:
            raise BizError(1503)
        
        return True
    
    async def get_dict_label(
        self, dict_type: str, dict_value: str
    ) -> Optional[str]:
        """
        Get the label for a dictionary value.
        
        Args:
            dict_type: Dictionary type code
            dict_value: Dictionary value
            
        Returns:
            Label string or None if not found
        """
        items = await self.get_dict_data_simple_list(dict_type)
        for item in items:
            if item["dict_value"] == dict_value:
                return item["dict_label"]
        return None
    
    async def invalidate_cache(self, dict_type: str) -> None:
        """
        Invalidate cache for a dictionary type.
        
        Called after dictionary modification.
        """
        cache_key = f"{self.CACHE_PREFIX}{dict_type}"
        Cache.delete(cache_key)
    
    def validate_dict_type_format(self, dict_type: str) -> None:
        """
        Validate dictionary type format.
        
        Format: ^dict_[a-z][a-z0-9_]*$
        
        Raises:
            BizError(1001): Invalid format
        """
        if not self.DICT_TYPE_PATTERN.match(dict_type):
            raise BizError(1001, msg="字典类型格式不正确，应为dict_开头的小写字母数字下划线")
    
    def validate_dict_value_format(self, dict_value: str) -> None:
        """
        Validate dictionary value format.
        
        Format: ^[A-Z][A-Z0-9_]*$
        
        Raises:
            BizError(1001): Invalid format
        """
        if not self.DICT_VALUE_PATTERN.match(dict_value):
            raise BizError(1001, msg="字典值格式不正确，应为大写字母数字下划线")
    
    def validate_color_type(self, color_type: str) -> None:
        """
        Validate color type.
        
        Valid: primary|success|warning|danger|neutral|info|purple|yellow
        
        Raises:
            BizError(1001): Invalid color type
        """
        if color_type and color_type not in self.VALID_COLOR_TYPES:
            valid_str = "|".join(sorted(self.VALID_COLOR_TYPES))
            raise BizError(1001, msg=f"颜色类型不正确，应为 {valid_str}")
