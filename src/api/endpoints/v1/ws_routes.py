"""
WebSocket Routes — User + Admin endpoints
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError

from src.config import settings
from src.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()


def decode_token(token: str) -> dict | None:
    """Décoder le JWT et retourner le payload, ou None si invalide."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role", "user")
        if user_id is None:
            return None
        logger.info(f"🔑 WS token decoded → user_id={user_id}, role={role}")
        return {"user_id": str(user_id), "role": role}
    except JWTError as e:
        logger.warning(f"❌ WS token invalid: {e}")
        return None


# ==========================================
# USER WEBSOCKET (mobile app)
# ==========================================

@router.websocket("/ws/transactions")
async def ws_user_transactions(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket pour les utilisateurs (app mobile Flutter).
    Reçoit les mises à jour de statut de leurs transactions.
    """
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload["user_id"]
    await ws_manager.connect_user(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Heartbeat ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect_user(user_id, websocket)
    except Exception as e:
        logger.error(f"WS user error: {e}")
        ws_manager.disconnect_user(user_id, websocket)


# ==========================================
# ADMIN WEBSOCKET (dashboard Next.js)
# ==========================================

@router.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket pour les administrateurs (dashboard Next.js).
    Reçoit les notifications de nouvelles transactions, etc.
    """
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Vérifier que c'est bien un admin
    if payload.get("role") not in ("admin", "agent"):
        logger.warning(f"⛔ WS admin rejected: user_id={payload['user_id']}, role={payload.get('role')}")
        await websocket.close(code=4003, reason="Admin access required")
        return

    admin_id = payload["user_id"]
    await ws_manager.connect_admin(admin_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect_admin(admin_id, websocket)
    except Exception as e:
        logger.error(f"WS admin error: {e}")
        ws_manager.disconnect_admin(admin_id, websocket)


# ==========================================
# DEBUG ENDPOINTS (retirer en production)
# ==========================================

@router.get("/ws/debug/connections")
async def debug_connections():
    """Voir toutes les connexions actives (users + admins)."""
    return ws_manager.get_debug_info()


@router.get("/ws/debug/test-admin-notify")
async def test_admin_notify():
    """Envoyer une notification test à tous les admins connectés."""
    test_data = {
        "type": "new_transaction",
        "transaction": {
            "id": "test-123",
            "reference": "TEST-001",
            "sender_name": "Test User",
            "receiver_name": "Test Receiver",
            "send_amount": 10000,
            "send_currency_code": "RUB",
            "receive_amount": 75000,
            "receive_currency_code": "XOF",
            "status": "FUNDS_DEPOSITED",
            "created_at": "2025-01-01T12:00:00Z",
        },
    }
    await ws_manager.notify_all_admins(test_data)
    info = ws_manager.get_debug_info()
    return {
        "sent": True,
        "admin_connections": info["admins"]["total_connections"],
    }