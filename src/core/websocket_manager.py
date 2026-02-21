# src/core/websocket_manager.py

import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gère les connexions WebSocket par utilisateur.
    """

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()

        if user_id not in self._connections:
            self._connections[user_id] = set()

        self._connections[user_id].add(websocket)
        logger.info(
            f"✅ WS connected: user={user_id} "
            f"(user_connections={len(self._connections[user_id])}, "
            f"total_users={len(self._connections)})"
        )

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(f"❌ WS disconnected: user={user_id}")

    async def notify_user(self, user_id: str, data: dict):
        # ✅ LOG CRITIQUE POUR LE DEBUG
        logger.info(
            f"📤 notify_user called: user_id={user_id!r} | "
            f"connected_users={list(self._connections.keys())}"
        )

        if user_id not in self._connections:
            logger.warning(
                f"⚠️ User {user_id!r} NOT in connections! "
                f"Available: {list(self._connections.keys())} "
                f"— Notification SKIPPED"
            )
            return

        dead_connections = set()

        for ws in self._connections[user_id]:
            try:
                await ws.send_json(data)
                logger.info(f"📤 Sent to user={user_id}: {data.get('event', '?')}")
            except Exception as e:
                logger.warning(f"Failed to send to user={user_id}: {e}")
                dead_connections.add(ws)

        for ws in dead_connections:
            self._connections[user_id].discard(ws)

        if user_id in self._connections and not self._connections[user_id]:
            del self._connections[user_id]

    async def broadcast(self, data: dict):
        for user_id in list(self._connections.keys()):
            await self.notify_user(user_id, data)

    @property
    def active_connections_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    @property
    def active_users_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()