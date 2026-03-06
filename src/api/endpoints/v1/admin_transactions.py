"""
╔══════════════════════════════════════════════════════════════════╗
║  ADMIN STATUS ROUTES — Changement de statut + ledger auto        ║
║  Placer dans: src/api/endpoints/v1/admin_status_routes.py        ║
║  Prefix: /api/v1/admin                                           ║
║                                                                  ║
║  SCÉNARIO INTÉGRÉ:                                               ║
║                                                                  ║
║  1. Client CI dépose 100,000 XOF via Wave CI                    ║
║     → Transaction créée (FUNDS_DEPOSITED)                        ║
║                                                                  ║
║  2. Admin vérifie le dépôt → PATCH .../status                    ║
║     body: { new_status: "IN_PROGRESS" }                          ║
║     → AUTO: DEBIT +100,000 XOF  wallet "Wave CI / XOF"          ║
║     → AUTO: DEBIT   +5,000 XOF  wallet "Fees XOF"               ║
║                                                                  ║
║  3. Agent RU paie le bénéficiaire → PATCH .../status             ║
║     body: { new_status: "COMPLETED" }                            ║
║     → AUTO: CREDIT -13,500 RUB  wallet "Sberbank / RUB"         ║
║                                                                  ║
║  4. Si annulation → PATCH .../status                             ║
║     body: { new_status: "CANCELLED", reason: "..." }             ║
║     → AUTO: Reverse de toutes les écritures existantes           ║
║                                                                  ║
║  RÉSOLUTION AUTOMATIQUE:                                         ║
║    Les wallets sont trouvés via payment_method / receiving_method ║
║    de la transaction. Override possible via wallet_id dans body.  ║
╚══════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.permission import agent_or_admin_required
from src.db.models import Transaction, TransactionStatus, TransactionStatusHistory
from src.db.session import get_session
from src.core.websocket_manager import ws_manager
from src.schemas.transaction import (
    VALID_TRANSITIONS,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from src.services.ledger_service import (
    ledger_service,
    LedgerError,
    AlreadyProcessedError,
    WalletNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin - Transactions"])


# =============================================================================
# ROUTE PRINCIPALE — Changement de statut + ledger automatique
# =============================================================================

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
    Met à jour le statut d'une transaction + enregistre dans le ledger.

    **Transitions + effets automatiques:**

    | Transition                        | Effet ledger                      |
    |-----------------------------------|-----------------------------------|
    | FUNDS_DEPOSITED → IN_PROGRESS     | DEBIT wallet collecte + frais     |
    | IN_PROGRESS     → COMPLETED       | CREDIT wallet décaissement        |
    | *               → CANCELLED       | Reverse des écritures existantes  |

    **Résolution automatique des wallets:**
    - Collection:   `tx.payment_method` + `tx.sender_currency`
    - Décaissement: `tx.receiving_method` + `tx.receiver_currency`
    - Frais:        `system@chapmoney.dev` + `tx.sender_currency`

    Vous pouvez forcer un wallet spécifique via `collection_wallet_id`,
    `disbursement_wallet_id`, ou `fee_wallet_id` dans le body.
    """

    # ── 1. Récupérer la transaction ──
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction introuvable",
        )

    old_status = transaction.status

    # ── 2. Valider la transition ──
    allowed = VALID_TRANSITIONS.get(old_status, set())
    if body.new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Transition invalide: {old_status.value} → {body.new_status.value}. "
                f"Autorisées: {[s.value for s in allowed]}"
            ),
        )

    now = datetime.now(timezone.utc)
    ledger_ref = None
    ledger_msg = None

    # ══════════════════════════════════════════════════════════════
    # 3. EFFETS LEDGER AUTOMATIQUES
    # ══════════════════════════════════════════════════════════════

    try:

        # ──────────────────────────────────────────────────────────
        # IN_PROGRESS → Phase 1: Collecte
        #
        # L'admin a vérifié que le client a bien déposé les fonds
        # via le moyen de paiement choisi (ex: Wave CI).
        #
        # → DEBIT wallet agent collecte  +sender_amount
        # → DEBIT wallet Chapmoney frais +fee_amount
        # ──────────────────────────────────────────────────────────
        if body.new_status == TransactionStatus.IN_PROGRESS:
            transaction.processed_at = now
            transaction.processed_by_admin_id = admin.id

            ltx = await ledger_service.record_collection(
                db,
                transaction,
                initiated_by_id=admin.id,
                collection_wallet_id=body.collection_wallet_id,
                fee_wallet_id=body.fee_wallet_id,
            )
            ledger_ref = ltx.reference
            ledger_msg = (
                f"Collecte: +{transaction.sender_amount} "
                f"{transaction.sender_currency} "
                f"via {transaction.payment_method}"
            )
            if transaction.fee_amount:
                ledger_msg += f" (frais: +{transaction.fee_amount})"

            logger.info(
                f"✅ {transaction.reference}: "
                f"FUNDS_DEPOSITED → IN_PROGRESS + collecte {ltx.reference}"
            )

        # ──────────────────────────────────────────────────────────
        # COMPLETED → Phase 2: Décaissement
        #
        # L'agent du pays de réception a payé le bénéficiaire
        # via la méthode de réception (ex: Sberbank).
        #
        # → CREDIT wallet agent décaissement  -receiver_amount
        # ──────────────────────────────────────────────────────────
        elif body.new_status == TransactionStatus.COMPLETED:
            transaction.completed_at = now

            ltx = await ledger_service.record_disbursement(
                db,
                transaction,
                initiated_by_id=admin.id,
                disbursement_wallet_id=body.disbursement_wallet_id,
            )
            ledger_ref = ltx.reference
            ledger_msg = (
                f"Décaissement: -{transaction.receiver_amount} "
                f"{transaction.receiver_currency} "
                f"via {transaction.receiving_method} "
                f"→ {transaction.recipient_name}"
            )

            logger.info(
                f"✅ {transaction.reference}: "
                f"IN_PROGRESS → COMPLETED + décaissement {ltx.reference}"
            )

        # ──────────────────────────────────────────────────────────
        # CANCELLED → Reverse
        #
        # Annulation: on crée des écritures inverses pour chaque
        # écriture déjà enregistrée (collecte et/ou décaissement).
        # ──────────────────────────────────────────────────────────
        elif body.new_status == TransactionStatus.CANCELLED:
            transaction.cancelled_at = now

            reversed_entries = await ledger_service.reverse_transaction(
                db,
                transaction,
                reason=body.reason or "Annulation admin",
                initiated_by_id=admin.id,
            )

            if reversed_entries:
                ledger_msg = f"{len(reversed_entries)} écritures annulées"
                logger.info(
                    f"✅ {transaction.reference}: "
                    f"→ CANCELLED + {len(reversed_entries)} reverse"
                )
            else:
                ledger_msg = "Aucune écriture ledger à annuler"

    except AlreadyProcessedError as e:
        # Déjà traité — on log mais on continue la mise à jour du statut
        logger.warning(f"⚠️ {transaction.reference}: {e}")
        ledger_msg = f"Déjà traité: {e}"

    except WalletNotFoundError as e:
        # Pas de wallet trouvé → bloquer la transition
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Impossible de traiter dans le ledger: {e}. "
                f"Vérifiez qu'un wallet agent actif existe pour "
                f"méthode='{transaction.payment_method}' / "
                f"devise='{transaction.sender_currency}', "
                f"ou spécifiez manuellement un wallet_id dans le body."
            ),
        )

    except LedgerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur ledger: {e}",
        )

    # ══════════════════════════════════════════════════════════════
    # 4. METTRE À JOUR LE STATUT
    # ══════════════════════════════════════════════════════════════

    transaction.status = body.new_status

    # ── 5. Audit trail ──
    history = TransactionStatusHistory(
        transaction_id=transaction.id,
        old_status=old_status,
        new_status=body.new_status,
        changed_by_admin_id=admin.id,
        reason=body.reason,
    )
    db.add(history)

    await db.commit()
    await db.refresh(transaction)

    # ══════════════════════════════════════════════════════════════
    # 6. NOTIFICATIONS WEBSOCKET
    # ══════════════════════════════════════════════════════════════

    # → Notifier le client
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

    # → Notifier tous les admins (synchro dashboard)
    await ws_manager.notify_all_admins({
        "type": "status_update",
        "transaction": {
            "id": str(transaction.id),
            "reference": transaction.reference,
            "status": body.new_status.value,
            "updated_at": transaction.updated_at.isoformat(),
            "ledger_reference": ledger_ref,
            "ledger_message": ledger_msg,
        },
    })

    return StatusUpdateResponse(
        transaction_id=str(transaction.id),
        reference=transaction.reference,
        old_status=old_status.value,
        new_status=body.new_status.value,
        updated_at=transaction.updated_at,
        ledger_reference=ledger_ref,
        ledger_message=ledger_msg,
    )


# =============================================================================
# ROUTE — Preview: quels wallets seront utilisés ?
# =============================================================================

@router.get("/transactions/{transaction_id}/resolve-wallets")
async def resolve_transaction_wallets(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_session),
    admin=Depends(agent_or_admin_required),
):
    """
    Preview avant action: montre quels wallets seront auto-résolus.

    Permet à l'admin de vérifier AVANT de changer le statut:
    - Quel wallet agent va recevoir le dépôt ?
    - Quel wallet agent va payer le bénéficiaire ?
    - Quel wallet va collecter les frais ?

    **Réponse type:**
    ```json
    {
      "collection": {
        "wallet_id": "...",
        "agent_name": "Agent Abidjan",
        "payment_method": "Wave CI",
        "currency_code": "XOF",
        "current_balance": 2500000,
        "will_debit": 100000,
        "balance_after": 2600000
      },
      "disbursement": {
        "wallet_id": "...",
        "agent_name": "Agent Moscou",
        "payment_method": "Sberbank",
        "currency_code": "RUB",
        "current_balance": 450000,
        "will_credit": 13500,
        "balance_after": 436500
      },
      "fee": { "wallet_id": "...", "fee_amount": 5000 }
    }
    ```
    """
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(404, "Transaction introuvable")

    return await ledger_service.preview_wallets(db, transaction)


# =============================================================================
# ROUTE — Résumé ledger d'une transaction
# =============================================================================

@router.get("/transactions/{transaction_id}/ledger")
async def get_transaction_ledger(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_session),
    admin=Depends(agent_or_admin_required),
):
    """
    Résumé des opérations ledger pour une transaction.

    Montre les 3 phases possibles:
    - **collection** (Phase 1 / IN_PROGRESS): wallet débité + frais
    - **disbursement** (Phase 2 / COMPLETED): wallet crédité
    - **correction** (CANCELLED): écritures inversées

    **Réponse type:**
    ```json
    {
      "reference": "tx1a2b3c4d5e",
      "status": "COMPLETED",
      "collection_done": true,
      "disbursement_done": true,
      "is_reversed": false,
      "total_entries": 3,
      "phases": {
        "collection": {
          "reference": "COL-250301...",
          "entries": [
            {"entry_type": "DEBIT", "amount": 100000, "currency_code": "XOF"},
            {"entry_type": "DEBIT", "amount": 5000, "currency_code": "XOF"}
          ]
        },
        "disbursement": {
          "reference": "DIS-250301...",
          "entries": [
            {"entry_type": "CREDIT", "amount": 13500, "currency_code": "RUB"}
          ]
        },
        "correction": null
      }
    }
    ```
    """
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(404, "Transaction introuvable")

    summary = await ledger_service.get_transaction_ledger_summary(
        db, transaction_id,
    )
    summary["reference"] = transaction.reference
    summary["status"] = (
        transaction.status.value
        if hasattr(transaction.status, "value")
        else str(transaction.status)
    )
    return summary