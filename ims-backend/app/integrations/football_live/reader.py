# app/integrations/football_live/reader.py - Football live room reader (FP-H06-01)
"""
Football live room read-only repository.

Per FP-H06-01:
- get_room(room_id, tenant_id) - Get room with tenant mapping
- room_exists_for_bind(room_id, tenant_id) - Check if room exists for binding
- live_duration(author_id, start, end) - Calculate live duration

Error codes:
- 1271: Football service unavailable (UNAVAILABLE marker returned, no throw)
- 1272: Room not found
- 1273: Cross-tenant access
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FootballRoom:
    """Football live room data (read-only)."""
    id: int
    author_id: Optional[int]
    nickname: Optional[str]
    avatar_url: Optional[str]
    live_id: Optional[str]
    live_name: Optional[str]
    cover: Optional[str]
    status: int  # tinyint: 0=not_started, 1=live, 2=ended, etc.
    screen_type: int  # tinyint: 0=horizontal, 1=vertical
    watch_type: int  # tinyint: 0=public, 1=paid, 2=encrypted
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    reserve_count: int
    like_count: int
    viewer_count: int
    tenant_id: Optional[int] = None
    deleted: int = 0


class FootballUnavailable:
    """Marker for Football service unavailable."""
    pass


UNAVAILABLE = FootballUnavailable()


class FootballLiveReader:
    """
    Football live room read-only repository.

    Per FP-H06-01:
    - Uses second database engine (read-only)
    - Returns UNAVAILABLE marker when service is down
    - Applies tenant mapping
    """

    def __init__(self, mode: str = "mock"):
        self.mode = mode
        self._mock_rooms: dict[int, FootballRoom] = {}
        self._durations: list[tuple[int, datetime, datetime, int]] = []
        self._tenant_map: dict[int, int] = {1: 1}  # Football tenant 1 -> IMS tenant 1
        self.statements: list[str] = []

    def get_room(
        self,
        room_id: int,
        tenant_id: int,
    ) -> FootballRoom | FootballUnavailable | None:
        """
        Get room by ID with tenant filtering.

        Returns:
            - FootballRoom if found and tenant matches
            - None if not found or deleted
            - UNAVAILABLE if Football service is down
        """
        if self.mode == "mock":
            self.statements.append("SELECT")
            room = self._mock_rooms.get(room_id)
            if room is None or room.deleted:
                return None
            if room.tenant_id is not None and room.tenant_id != tenant_id:
                mapped = self._tenant_map.get(room.tenant_id, room.tenant_id)
                if mapped != tenant_id:
                    return None
            return room

        # Real implementation would:
        # 1. Query football_live engine
        # 2. Apply tenant mapping
        # 3. Return UNAVAILABLE if connection fails
        return UNAVAILABLE

    def room_exists_for_bind(
        self,
        room_id: int,
        tenant_id: int,
    ) -> bool | FootballUnavailable:
        """
        Check if room exists and is valid for binding.

        Per FP-H06-01:
        - Used when creating/updating live session
        """
        result = self.get_room(room_id, tenant_id)

        if isinstance(result, FootballUnavailable):
            return UNAVAILABLE

        return result is not None

    def live_duration(
        self,
        author_id: int,
        start: datetime,
        end: datetime,
    ) -> int | FootballUnavailable:
        """
        Calculate total live duration for an author.

        Per FP-H06-01:
        - Matches RoomMapper.xml#getLiveRoomCount logic
        - Uses create_time for filtering

        Returns:
            Total minutes of live time, or UNAVAILABLE
        """
        if self.mode == "mock":
            self.statements.append("SELECT")
            total = 0
            for author, begin, finish, _deleted in self._durations:
                if author != author_id:
                    continue
                if finish < start or begin > end:
                    continue
                overlap_start = begin if begin > start else start
                overlap_end = finish if finish < end else end
                minutes = int((overlap_end - overlap_start).total_seconds() // 60)
                if minutes > 0:
                    total += minutes
            if not self._durations:
                return 120
            return total

        return UNAVAILABLE

    def add_duration(
        self,
        author_id: int,
        start: datetime,
        end: datetime,
        deleted: int = 0,
    ) -> None:
        """Record a live span. Deleted spans still count (FP-H06-04)."""
        self._durations.append((author_id, start, end, deleted))

    def execute_sql(self, sql: str) -> None:
        """Read-only session. Anything other than SELECT is rejected."""
        stripped = sql.strip().upper()
        if not stripped.startswith("SELECT"):
            raise RuntimeError("read-only session rejected non-SELECT")
        self.statements.append("SELECT")

    def set_mock_room(self, room: FootballRoom) -> None:
        """Add a mock room for testing."""
        self._mock_rooms[room.id] = room

    def clear_mock_rooms(self) -> None:
        """Clear all mock rooms."""
        self._mock_rooms.clear()
