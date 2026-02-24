
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.permission import agent_or_admin_required
from src.db.models import Transaction, TransactionStatus, TransactionStatusHistory
from src.db.session import get_session
from src.core.websocket_manager import ws_manager
from src.schemas.transaction import VALID_TRANSITIONS, StatusUpdateRequest, StatusUpdateResponse

router = APIRouter(prefix="/admin", tags=["Admin - Transactions"])



# ============================================
# TRANSITIONS VALIDES
# ============================================

VALID_TRANSITIONS: dict[TransactionStatus, set[TransactionStatus]] = {
    TransactionStatus.FUNDS_DEPOSITED: {
        TransactionStatus.IN_PROGRESS,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.IN_PROGRESS: {
        TransactionStatus.COMPLETED,
        TransactionStatus.CANCELLED,
    },
}


# ============================================
# ROUTE
# ============================================

@router.patch(
    "/transactions/{transaction_id}/status",
    response_model=StatusUpdateResponse,
)
async def update_transaction_status(
    transaction_id: UUID,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_session),
    admin=Depends(agent_or_admin_required),
):
    """
    Met à jour le statut d'une transaction.

    Transitions valides:
    - FUNDS_DEPOSITED → IN_PROGRESS | CANCELLED
    - IN_PROGRESS → COMPLETED | CANCELLED

    ✅ Notifie automatiquement l'utilisateur via WebSocket.
    """

    # 1. Récupérer la transaction
    transaction = await db.get(Transaction, transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction introuvable",
        )

    old_status = transaction.status

    # 2. Valider la transition
    allowed = VALID_TRANSITIONS.get(old_status, set())

    if body.new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Transition invalide: {old_status} → {body.new_status}. "
                f"Transitions autorisées: {[s.value for s in allowed]}"
            ),
        )

    # ============================================
    # 1️⃣ Update métier selon statut
    # ============================================

    now = datetime.now(timezone.utc)

    if body.new_status == TransactionStatus.IN_PROGRESS:
        transaction.processed_at = now
        transaction.processed_by_admin_id = admin.id

    elif body.new_status == TransactionStatus.COMPLETED:
        transaction.completed_at = now

    elif body.new_status == TransactionStatus.CANCELLED:
        transaction.cancelled_at = now

    elif body.new_status == TransactionStatus.EXPIRED:
        transaction.expired_at = now

    transaction.status = body.new_status

    # ============================================
    # 2️⃣ Audit history (critique en fintech)
    # ============================================

    history = TransactionStatusHistory(
        transaction_id=transaction.id,
        old_status=old_status,
        new_status=body.new_status,
        changed_by_admin_id=admin.id,
        reason=body.reason
    )

    db.add(history)

    await db.commit()
    await db.refresh(transaction)

    # 4. ✅ Notifier l'utilisateur via WebSocket
    await ws_manager.notify_user(
        user_id=str(transaction.sender_id),
        data={
            "event": "transaction_status_updated",
            "data": {
                "transaction_id": str(transaction.id),
                "old_status": old_status.value,
                "new_status": body.new_status.value,
                "reference": transaction.reference,
                "updated_at": transaction.updated_at.isoformat(),
            },
        },
    )
    
    # ============================================
    # 4️⃣ ✅ Notifier TOUS les admins connectés
    #    (synchro entre admins sur le dashboard)
    # ============================================
    await ws_manager.notify_all_admins({
        "type": "status_update",
        "transaction": {
            "id": str(transaction.id),
            "reference": transaction.reference,
            "status": body.new_status.value,
            "updated_at": transaction.updated_at.isoformat(),
        },
    })


    return StatusUpdateResponse(
        transaction_id=str(transaction.id),
        old_status=old_status.value,
        new_status=body.new_status.value,
        reference=transaction.reference,
        updated_at=transaction.updated_at,
    )


