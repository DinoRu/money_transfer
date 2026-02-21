# app/api/routes/ws_routes.py

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import jwt, JWTError

from src.auth.permission import agent_or_admin_required
from src.config import settings
from src.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_user_id_from_token(token: str) -> str | None:
    """Vérifie le JWT et extrait le user_id."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload.get("sub")  # ou "user_id" selon ton JWT
    except JWTError as e:
        logger.warning(f"Invalid WS token: {e}")
        return None


@router.websocket("/ws/transactions")
async def websocket_transactions(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint pour les mises à jour en temps réel.

    Connexion:
        ws://host/ws/transactions?token=<jwt_token>

    Messages reçus par le client:
    {
        "event": "transaction_status_updated",
        "data": {
            "transaction_id": "uuid",
            "new_status": "IN_PROGRESS",
            "old_status": "FUNDS_DEPOSITED",
            "reference": "TXN-20260215-XXXX",
            "updated_at": "2026-02-15T14:30:00Z"
        }
    }
    """
    # ✅ Authentifier AVANT d'accepter la connexion
    user_id = _extract_user_id_from_token(token)

    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Connecter
    await ws_manager.connect(websocket, user_id)

    try:
        # Garder la connexion ouverte
        while True:
            # Écouter les messages du client (heartbeat/ping)
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WS error for user={user_id}: {e}")
        ws_manager.disconnect(websocket, user_id)
        
        


# ============================================
# 🔧 DEBUG ENDPOINTS (supprimer en production)
# ============================================

@router.get("/ws/debug/connections")
async def debug_connections(admin=Depends(agent_or_admin_required)):
    """Liste toutes les connexions WS actives."""
    users = {
        uid: len(ws_set) for uid, ws_set in ws_manager._connections.items()
    }
    return {
        "active_users": ws_manager.active_users_count,
        "active_connections": ws_manager.active_connections_count,
        "users": users,
    }


@router.get("/ws/debug/test-notify/{user_id}")
async def debug_test_notify(user_id: str, admin=Depends(agent_or_admin_required)):
    """Envoie une fausse notification à un user pour tester."""
    is_connected = user_id in ws_manager._connections

    await ws_manager.notify_user(
        user_id=user_id,
        data={
            "event": "transaction_status_updated",
            "data": {
                "transaction_id": "debug-test-000",
                "old_status": "FUNDS_DEPOSITED",
                "new_status": "IN_PROGRESS",
                "reference": "TEST-DEBUG",
                "updated_at": "2026-02-21T00:00:00Z",
            },
        },
    )

    return {
        "user_id": user_id,
        "is_connected": is_connected,
        "connections": len(ws_manager._connections.get(user_id, set())),
        "result": "sent" if is_connected else "SKIPPED — user not connected",
    }
