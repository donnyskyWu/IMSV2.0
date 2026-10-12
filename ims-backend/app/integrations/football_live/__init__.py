# app/integrations/football_live - Football live room reader (FW-H06)
"""
Football live room read-only integration.

Per FP-H06-01:
- Read-only access to Football live_room table
- Second database engine with SELECT-only permissions
- Error codes: 1271 (unavailable), 1272 (room not found), 1273 (cross-tenant)

Note: Uses stub table in dev/test, real shenyu-live in production.
"""

from app.integrations.football_live.reader import FootballLiveReader

__all__ = ["FootballLiveReader"]
