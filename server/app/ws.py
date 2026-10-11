import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import WebSocket


@dataclass
class RoomConnection:
    ws: WebSocket
    user_id: int
    username: str


@dataclass
class ConnectionManager:
    """In-process WebSocket rooms, one room per board.

    For horizontal scaling this would sit behind a Redis pub/sub fanout;
    see README "Design notes & scaling".
    """

    rooms: dict[int, list[RoomConnection]] = field(default_factory=dict)

    async def connect(self, board_id: int, ws: WebSocket, user_id: int, username: str) -> None:
        self.rooms.setdefault(board_id, []).append(RoomConnection(ws, user_id, username))

    def disconnect(self, board_id: int, ws: WebSocket) -> None:
        room = self.rooms.get(board_id, [])
        self.rooms[board_id] = [c for c in room if c.ws is not ws]
        if not self.rooms[board_id]:
            del self.rooms[board_id]

    def presence(self, board_id: int) -> list[dict]:
        seen: dict[int, dict] = {}
        for c in self.rooms.get(board_id, []):
            seen[c.user_id] = {"id": c.user_id, "username": c.username}
        return list(seen.values())

    async def broadcast(self, board_id: int, message: dict) -> None:
        room = list(self.rooms.get(board_id, []))
        results = await asyncio.gather(
            *(c.ws.send_json(message) for c in room), return_exceptions=True
        )
        for conn, result in zip(room, results):
            if isinstance(result, Exception):
                self.disconnect(board_id, conn.ws)

    async def broadcast_presence(self, board_id: int) -> None:
        await self.broadcast(board_id, event("presence", {"users": self.presence(board_id)}))


def event(type_: str, data: dict, actor_id: int | None = None) -> dict:
    return {
        "type": type_,
        "data": data,
        "actor_id": actor_id,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
