"""种子脚本取时。禁止 datetime.now，统一走 app.core.clock。"""

from datetime import datetime

from app.core.clock import get_now


def seed_now() -> datetime:
    """北京时间墙上时钟。去掉时区后写入无时区的 DATETIME 列。"""
    current = get_now()
    if current.tzinfo is not None:
        return current.replace(tzinfo=None)
    return current
