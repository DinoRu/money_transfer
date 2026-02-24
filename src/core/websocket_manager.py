"""
WebSocket Connection Manager — Users + Admins
Gère les connexions WebSocket pour les utilisateurs ET les administrateurs.
"""

import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Singleton pour gérer toutes les connexions WebSocket."""

    def __init__(self):
        # Connexions utilisateurs: { user_id: [WebSocket, ...] }
        self.user_connections: Dict[str, List[WebSocket]] = {}
        # Connexions admins: { admin_id: [WebSocket, ...] }
        self.admin_connections: Dict[str, List[WebSocket]] = {}

    # ==========================================
    # USER CONNECTIONS
    # ==========================================

    async def connect_user(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        logger.info(
            f"✅ WS user connected: user_id={user_id} "
            f"(total user connections: {self._count_user_connections()})"
        )

    def disconnect_user(self, user_id: str, websocket: WebSocket):
        if user_id in self.user_connections:
            self.user_connections[user_id] = [
                ws for ws in self.user_connections[user_id] if ws != websocket
            ]
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        logger.info(
            f"🔌 WS user disconnected: user_id={user_id} "
            f"(remaining: {self._count_user_connections()})"
        )

    async def notify_user(self, user_id: str, data: dict):
        """Envoyer une notification à un utilisateur spécifique."""
        user_id_str = str(user_id)
        connections = self.user_connections.get(user_id_str, [])

        if not connections:
            logger.warning(
                f"📤 notify_user: user_id='{user_id_str}' NOT connected. "
                f"Connected users: {list(self.user_connections.keys())}"
            )
            return

        logger.info(f"📤 notify_user: sending to user_id='{user_id_str}' ({len(connections)} conn)")
        dead = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to user {user_id_str}: {e}")
                dead.append(ws)

        for ws in dead:
            self.disconnect_user(user_id_str, ws)

    # ==========================================
    # ADMIN CONNECTIONS
    # ==========================================

    async def connect_admin(self, admin_id: str, websocket: WebSocket):
        await websocket.accept()
        if admin_id not in self.admin_connections:
            self.admin_connections[admin_id] = []
        self.admin_connections[admin_id].append(websocket)
        logger.info(
            f"✅ WS admin connected: admin_id={admin_id} "
            f"(total admin connections: {self._count_admin_connections()})"
        )

    def disconnect_admin(self, admin_id: str, websocket: WebSocket):
        if admin_id in self.admin_connections:
            self.admin_connections[admin_id] = [
                ws for ws in self.admin_connections[admin_id] if ws != websocket
            ]
            if not self.admin_connections[admin_id]:
                del self.admin_connections[admin_id]
        logger.info(
            f"🔌 WS admin disconnected: admin_id={admin_id} "
            f"(remaining: {self._count_admin_connections()})"
        )

    async def notify_all_admins(self, data: dict):
        """Envoyer une notification à TOUS les admins connectés."""
        if not self.admin_connections:
            logger.info("📤 notify_all_admins: no admins connected, skipping")
            return

        total = self._count_admin_connections()
        logger.info(f"📤 notify_all_admins: broadcasting to {total} admin connection(s)")

        dead_pairs = []
        for admin_id, connections in self.admin_connections.items():
            for ws in connections:
                try:
                    await ws.send_json(data)
                except Exception as e:
                    logger.error(f"Failed to send to admin {admin_id}: {e}")
                    dead_pairs.append((admin_id, ws))

        for admin_id, ws in dead_pairs:
            self.disconnect_admin(admin_id, ws)

    # ==========================================
    # DEBUG
    # ==========================================

    def get_debug_info(self) -> dict:
        return {
            "users": {
                "active_users": len(self.user_connections),
                "total_connections": self._count_user_connections(),
                "user_ids": {uid: len(conns) for uid, conns in self.user_connections.items()},
            },
            "admins": {
                "active_admins": len(self.admin_connections),
                "total_connections": self._count_admin_connections(),
                "admin_ids": {aid: len(conns) for aid, conns in self.admin_connections.items()},
            },
        }

    def _count_user_connections(self) -> int:
        return sum(len(conns) for conns in self.user_connections.values())

    def _count_admin_connections(self) -> int:
        return sum(len(conns) for conns in self.admin_connections.values())


# Singleton global
ws_manager = ConnectionManager()