"""
╔══════════════════════════════════════════════════════════════════╗
║  LEDGER SERVICE — Comptabilité double-entrée Chapmoney           ║
║  Placer dans: src/services/ledger_service.py                     ║
║                                                                  ║
║  CONVENTIONS:                                                    ║
║    DEBIT  = wallet REÇOIT des fonds  → solde AUGMENTE (+)        ║
║    CREDIT = wallet DÉCAISSE des fonds → solde DIMINUE  (−)       ║
║                                                                  ║
║  SCÉNARIO TRANSFERT CLIENT:                                      ║
║                                                                  ║
║  Ex: Client CI envoie 100,000 XOF via Wave CI → RU Sberbank     ║
║                                                                  ║
║  Phase 1 — FUNDS_DEPOSITED → IN_PROGRESS:                        ║
║    Admin confirme avoir vu le dépôt Wave CI du client.           ║
║    → DEBIT  +100,000 XOF   wallet "Wave CI / XOF"    (collecte) ║
║    → DEBIT    +5,000 XOF   wallet "Fees XOF"         (frais)    ║
║                                                                  ║
║  Phase 2 — IN_PROGRESS → COMPLETED:                              ║
║    Agent RU paie le bénéficiaire, admin confirme.                ║
║    → CREDIT  -13,500 RUB   wallet "Sberbank / RUB"   (paiement) ║
║                                                                  ║
║  RÉSOLUTION AUTOMATIQUE DES WALLETS:                             ║
║    Collection:   tx.payment_method + tx.sender_currency          ║
║                  → AgentAccount(payment_method_name, currency)   ║
║    Décaissement: tx.receiving_method + tx.receiver_currency      ║
║                  → AgentAccount(payment_method_name, currency)   ║
║    Frais:        User(email=system@chapmoney.dev) + currency     ║
╚══════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, func, case as sa_case
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    User, Transaction, TransactionStatus,
    AgentAccount, LedgerTx, LedgerEntry,
    LedgerEntryType, LedgerCategory,
    Settlement, SettlementStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class LedgerError(Exception):
    pass


class InsufficientBalanceError(LedgerError):
    def __init__(self, wallet_id: UUID, current: Decimal, required: Decimal):
        self.wallet_id = wallet_id
        super().__init__(
            f"Solde insuffisant wallet {wallet_id}: "
            f"dispo={current}, requis={required}"
        )


class AccountNotFoundError(LedgerError):
    pass


class WalletNotFoundError(LedgerError):
    pass


class WalletInactiveError(LedgerError):
    pass


class AlreadyProcessedError(LedgerError):
    pass


# =============================================================================
# REFERENCE GENERATOR
# =============================================================================

def generate_ledger_ref(prefix: str = "LDG") -> str:
    ts = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    return f"{prefix}-{ts}-{uuid4().hex[:6].upper()}"


# =============================================================================
# LEDGER SERVICE
# =============================================================================

class LedgerService:

    # =========================================================================
    # CORE — Écriture atomique sur un wallet
    # =========================================================================

    async def _create_entry(
        self,
        session: AsyncSession,
        wallet_id: UUID,
        ledger_tx_id: UUID,
        entry_type: LedgerEntryType,
        amount: Decimal,
        currency_code: str,
        note: Optional[str] = None,
        skip_balance_check: bool = False,
    ) -> LedgerEntry:
        """
        Crée une écriture comptable et met à jour le solde.
        ⚠️ Doit être dans une transaction SQL active. Ne fait PAS de commit.
        """
        if amount <= 0:
            raise LedgerError(f"Montant doit être > 0, reçu: {amount}")

        # Lock le wallet (FOR UPDATE → sérialisé, anti race-condition)
        stmt = select(AgentAccount).where(
            AgentAccount.id == wallet_id
        ).with_for_update()
        wallet = (await session.execute(stmt)).scalar_one_or_none()

        if not wallet:
            raise WalletNotFoundError(f"Wallet {wallet_id} introuvable")
        if not wallet.is_active:
            raise WalletInactiveError(f"Wallet {wallet_id} désactivé")

        # Calculer le nouveau solde
        if entry_type == LedgerEntryType.DEBIT:
            new_balance = wallet.balance + amount
        else:  # CREDIT
            new_balance = wallet.balance - amount
            if not skip_balance_check and not wallet.can_debit(amount):
                raise InsufficientBalanceError(
                    wallet_id, wallet.balance, amount,
                )

        # Écriture immutable
        entry = LedgerEntry(
            id=uuid4(),
            ledger_tx_id=ledger_tx_id,
            wallet_id=wallet_id,
            entry_type=entry_type,
            amount=amount,
            currency_code=currency_code,
            balance_after=new_balance,
            note=note,
        )
        session.add(entry)

        # Solde cache
        wallet.balance = new_balance
        wallet.updated_at = datetime.now(timezone.utc)
        session.add(wallet)

        logger.info(
            f"📒 {entry_type.value} {amount} {currency_code} "
            f"wallet={wallet_id} → solde={new_balance}"
        )
        return entry

    # =========================================================================
    # WALLET RESOLUTION — Trouver le wallet automatiquement
    # =========================================================================

    async def resolve_wallet(
        self,
        session: AsyncSession,
        method_name: str,
        currency_code: str,
    ) -> AgentAccount:
        """
        Trouve le wallet agent actif pour une méthode + devise.

        Matching:
          AgentAccount.payment_method_name == method_name
          AgentAccount.currency_code == currency_code

        Ex: ("Wave CI", "XOF") → Wallet agent CI pour Wave
            ("Sberbank", "RUB") → Wallet agent RU pour Sberbank
        """
        stmt = select(AgentAccount).where(
            AgentAccount.payment_method_name == method_name,
            AgentAccount.currency_code == currency_code,
            AgentAccount.is_active == True,
        )
        wallet = (await session.execute(stmt)).scalar_one_or_none()

        if not wallet:
            raise WalletNotFoundError(
                f"Aucun wallet actif pour méthode='{method_name}' "
                f"devise='{currency_code}'. "
                f"Créez un wallet agent avec ce couple dans /agent-accounts."
            )
        return wallet

    async def resolve_fee_wallet(
        self,
        session: AsyncSession,
        currency_code: str,
    ) -> Optional[AgentAccount]:
        """
        Trouve le wallet Chapmoney System (frais) pour une devise.
        Cherche un wallet dont l'agent a email='system@chapmoney.dev'.
        """
        stmt = (
            select(AgentAccount)
            .join(User, AgentAccount.agent_id == User.id)
            .where(
                User.email == "system@chapmoney.dev",
                AgentAccount.currency_code == currency_code,
                AgentAccount.is_active == True,
            )
        )
        wallet = (await session.execute(stmt)).scalar_one_or_none()

        if not wallet:
            logger.warning(
                f"⚠️ Pas de wallet frais pour {currency_code}. "
                f"Frais non comptabilisés."
            )
        return wallet

    # =========================================================================
    # PREVIEW — Quels wallets seront utilisés ? (avant action)
    # =========================================================================

    async def preview_wallets(
        self,
        session: AsyncSession,
        transaction: Transaction,
    ) -> dict:
        """
        Retourne les wallets qui seront auto-résolus pour cette transaction.
        Utilisé par GET /transactions/{id}/resolve-wallets.
        """
        result = {
            "transaction_id": str(transaction.id),
            "reference": transaction.reference,
            "collection": None,
            "disbursement": None,
            "fee": None,
        }

        # Collection
        try:
            w = await self.resolve_wallet(
                session, transaction.payment_method, transaction.sender_currency,
            )
            agent = await session.get(User, w.agent_id)
            result["collection"] = {
                "wallet_id": str(w.id),
                "agent_name": agent.full_name if agent else None,
                "payment_method": w.payment_method_name,
                "currency_code": w.currency_code,
                "current_balance": float(w.balance),
                "will_debit": float(transaction.sender_amount),
                "balance_after": float(w.balance + transaction.sender_amount),
            }
        except WalletNotFoundError as e:
            result["collection"] = {"error": str(e)}

        # Disbursement
        try:
            w = await self.resolve_wallet(
                session, transaction.receiving_method, transaction.receiver_currency,
            )
            agent = await session.get(User, w.agent_id)
            result["disbursement"] = {
                "wallet_id": str(w.id),
                "agent_name": agent.full_name if agent else None,
                "payment_method": w.payment_method_name,
                "currency_code": w.currency_code,
                "current_balance": float(w.balance),
                "will_credit": float(transaction.receiver_amount),
                "balance_after": float(w.balance - transaction.receiver_amount),
            }
        except WalletNotFoundError as e:
            result["disbursement"] = {"error": str(e)}

        # Fee
        fee_wallet = await self.resolve_fee_wallet(
            session, transaction.sender_currency,
        )
        if fee_wallet:
            result["fee"] = {
                "wallet_id": str(fee_wallet.id),
                "currency_code": fee_wallet.currency_code,
                "fee_amount": float(transaction.fee_amount or 0),
            }
        else:
            result["fee"] = {
                "error": f"Pas de wallet frais pour {transaction.sender_currency}"
            }

        return result

    # =========================================================================
    # PHASE 1 — COLLECTE (FUNDS_DEPOSITED → IN_PROGRESS)
    #
    # L'admin confirme avoir reçu le dépôt du client.
    # → DEBIT  wallet collecte  +sender_amount
    # → DEBIT  wallet frais     +fee_amount
    # =========================================================================

    async def record_collection(
        self,
        session: AsyncSession,
        transaction: Transaction,
        initiated_by_id: UUID,
        collection_wallet_id: Optional[UUID] = None,
        fee_wallet_id: Optional[UUID] = None,
    ) -> LedgerTx:
        """
        Phase 1: Enregistre la collecte des fonds du client.
        Déclenché automatiquement sur transition → IN_PROGRESS.

        Résolution auto si wallet_id non fourni:
          tx.payment_method + tx.sender_currency → collection wallet
          system@chapmoney.dev + tx.sender_currency → fee wallet
        """
        # Anti-doublon
        existing = (await session.execute(
            select(LedgerTx).where(
                LedgerTx.transaction_id == transaction.id,
                LedgerTx.category == LedgerCategory.TRANSACTION_IN,
            )
        )).scalar_one_or_none()
        if existing:
            raise AlreadyProcessedError(
                f"Collecte déjà enregistrée: {existing.reference}"
            )

        sender_amount = Decimal(str(transaction.sender_amount))
        fee_amount = Decimal(str(transaction.fee_amount)) if transaction.fee_amount else Decimal("0")

        # ── Résoudre wallet collecte ──
        if collection_wallet_id:
            coll_wallet = await session.get(AgentAccount, collection_wallet_id)
            if not coll_wallet:
                raise WalletNotFoundError(f"Wallet {collection_wallet_id} introuvable")
        else:
            coll_wallet = await self.resolve_wallet(
                session, transaction.payment_method, transaction.sender_currency,
            )

        # ── LedgerTx ──
        ledger_tx = LedgerTx(
            id=uuid4(),
            reference=generate_ledger_ref("COL"),
            transaction_id=transaction.id,
            category=LedgerCategory.TRANSACTION_IN,
            description=(
                f"Collecte {transaction.reference}: "
                f"{sender_amount} {transaction.sender_currency} "
                f"via {transaction.payment_method} "
                f"→ {transaction.recipient_name}"
            ),
            exchange_rate=transaction.conversion_rate,
            initiated_by_id=initiated_by_id,
        )
        session.add(ledger_tx)

        # ── DEBIT wallet collecte ──
        await self._create_entry(
            session, coll_wallet.id, ledger_tx.id,
            LedgerEntryType.DEBIT, sender_amount,
            transaction.sender_currency,
            note=(
                f"Dépôt client {transaction.reference} "
                f"via {transaction.payment_method} "
                f"(bénéf: {transaction.recipient_name})"
            ),
        )

        # ── DEBIT wallet frais ──
        if fee_amount > 0:
            fw = None
            if fee_wallet_id:
                fw = await session.get(AgentAccount, fee_wallet_id)
            if not fw:
                fw = await self.resolve_fee_wallet(
                    session, transaction.sender_currency,
                )

            if fw:
                await self._create_entry(
                    session, fw.id, ledger_tx.id,
                    LedgerEntryType.DEBIT, fee_amount,
                    transaction.sender_currency,
                    note=f"Frais transfert {transaction.reference}",
                )

        logger.info(
            f"✅ COLLECTE {transaction.reference}: "
            f"+{sender_amount} {transaction.sender_currency} "
            f"sur {coll_wallet.payment_method_name} "
            f"(frais: +{fee_amount})"
        )
        return ledger_tx

    # =========================================================================
    # PHASE 2 — DÉCAISSEMENT (IN_PROGRESS → COMPLETED)
    #
    # L'agent du pays de réception paie le bénéficiaire.
    # L'admin confirme → CREDIT wallet décaissement  -receiver_amount
    # =========================================================================

    async def record_disbursement(
        self,
        session: AsyncSession,
        transaction: Transaction,
        initiated_by_id: UUID,
        disbursement_wallet_id: Optional[UUID] = None,
    ) -> LedgerTx:
        """
        Phase 2: Enregistre le décaissement au bénéficiaire.
        Déclenché automatiquement sur transition → COMPLETED.

        Résolution auto si wallet_id non fourni:
          tx.receiving_method + tx.receiver_currency → disbursement wallet
        """
        # Anti-doublon
        existing = (await session.execute(
            select(LedgerTx).where(
                LedgerTx.transaction_id == transaction.id,
                LedgerTx.category == LedgerCategory.TRANSACTION_OUT,
            )
        )).scalar_one_or_none()
        if existing:
            raise AlreadyProcessedError(
                f"Décaissement déjà enregistré: {existing.reference}"
            )

        # Vérifier que Phase 1 est faite
        phase1 = (await session.execute(
            select(LedgerTx).where(
                LedgerTx.transaction_id == transaction.id,
                LedgerTx.category == LedgerCategory.TRANSACTION_IN,
            )
        )).scalar_one_or_none()
        if not phase1:
            raise LedgerError(
                f"Impossible de décaisser {transaction.reference}: "
                f"la collecte (Phase 1 / IN_PROGRESS) n'a pas été enregistrée."
            )

        receiver_amount = Decimal(str(transaction.receiver_amount))

        # ── Résoudre wallet décaissement ──
        if disbursement_wallet_id:
            disb_wallet = await session.get(AgentAccount, disbursement_wallet_id)
            if not disb_wallet:
                raise WalletNotFoundError(
                    f"Wallet {disbursement_wallet_id} introuvable"
                )
        else:
            disb_wallet = await self.resolve_wallet(
                session, transaction.receiving_method, transaction.receiver_currency,
            )

        # ── LedgerTx ──
        ledger_tx = LedgerTx(
            id=uuid4(),
            reference=generate_ledger_ref("DIS"),
            transaction_id=transaction.id,
            category=LedgerCategory.TRANSACTION_OUT,
            description=(
                f"Paiement {transaction.reference}: "
                f"{receiver_amount} {transaction.receiver_currency} "
                f"via {transaction.receiving_method} "
                f"→ {transaction.recipient_name} ({transaction.recipient_phone})"
            ),
            exchange_rate=transaction.conversion_rate,
            initiated_by_id=initiated_by_id,
        )
        session.add(ledger_tx)

        # ── CREDIT wallet décaissement ──
        await self._create_entry(
            session, disb_wallet.id, ledger_tx.id,
            LedgerEntryType.CREDIT, receiver_amount,
            transaction.receiver_currency,
            note=(
                f"Paiement {transaction.recipient_name} "
                f"({transaction.recipient_phone}) "
                f"réf: {transaction.reference}"
            ),
            # L'agent peut aller en négatif temporairement → settlement à faire
            skip_balance_check=True,
        )

        logger.info(
            f"✅ DÉCAISSEMENT {transaction.reference}: "
            f"-{receiver_amount} {transaction.receiver_currency} "
            f"sur {disb_wallet.payment_method_name} "
            f"→ {transaction.recipient_name}"
        )
        return ledger_tx

    # =========================================================================
    # ANNULATION — Reverse toutes les écritures
    # =========================================================================

    async def reverse_transaction(
        self,
        session: AsyncSession,
        transaction: Transaction,
        reason: str,
        initiated_by_id: UUID,
    ) -> List[LedgerEntry]:
        """
        Crée des écritures inverses pour chaque écriture originale.
        Déclenché automatiquement sur transition → CANCELLED.
        """
        # Trouver toutes les écritures liées
        stmt = (
            select(LedgerEntry)
            .join(LedgerTx, LedgerEntry.ledger_tx_id == LedgerTx.id)
            .where(LedgerTx.transaction_id == transaction.id)
            .order_by(LedgerEntry.created_at)
        )
        originals = list((await session.execute(stmt)).scalars().all())

        if not originals:
            logger.info(f"Aucune écriture à annuler pour {transaction.reference}")
            return []

        # Vérifier qu'il n'y a pas déjà un reverse
        existing_rev = (await session.execute(
            select(LedgerTx).where(
                LedgerTx.transaction_id == transaction.id,
                LedgerTx.category == LedgerCategory.CORRECTION,
            )
        )).scalar_one_or_none()
        if existing_rev:
            raise AlreadyProcessedError(
                f"Annulation déjà enregistrée: {existing_rev.reference}"
            )

        ledger_tx = LedgerTx(
            id=uuid4(),
            reference=generate_ledger_ref("REV"),
            transaction_id=transaction.id,
            category=LedgerCategory.CORRECTION,
            description=f"ANNULATION {transaction.reference}: {reason}",
            initiated_by_id=initiated_by_id,
        )
        session.add(ledger_tx)

        entries = []
        for orig in originals:
            reverse_type = (
                LedgerEntryType.CREDIT
                if orig.entry_type == LedgerEntryType.DEBIT
                else LedgerEntryType.DEBIT
            )
            entry = await self._create_entry(
                session, orig.wallet_id, ledger_tx.id,
                reverse_type, orig.amount, orig.currency_code,
                note=f"Annulation: {reason} (réf: {transaction.reference})",
                skip_balance_check=True,
            )
            entries.append(entry)

        logger.info(
            f"✅ ANNULATION {transaction.reference}: "
            f"{len(entries)} écritures inversées"
        )
        return entries

    # =========================================================================
    # QUERY — Résumé ledger pour une transaction
    # =========================================================================

    async def get_transaction_ledger_summary(
        self,
        session: AsyncSession,
        transaction_id: UUID,
    ) -> dict:
        """Résumé des opérations ledger (collecte, décaissement, correction)."""
        ledger_txs = (await session.execute(
            select(LedgerTx)
            .where(LedgerTx.transaction_id == transaction_id)
            .order_by(LedgerTx.created_at)
        )).scalars().all()

        phases = {
            "collection": None,
            "disbursement": None,
            "correction": None,
        }
        total_entries = 0

        for ltx in ledger_txs:
            entries = (await session.execute(
                select(LedgerEntry)
                .where(LedgerEntry.ledger_tx_id == ltx.id)
                .order_by(LedgerEntry.created_at)
            )).scalars().all()

            phase_data = {
                "ledger_tx_id": str(ltx.id),
                "reference": ltx.reference,
                "category": ltx.category.value if hasattr(ltx.category, "value") else str(ltx.category),
                "description": ltx.description,
                "created_at": ltx.created_at.isoformat() if ltx.created_at else None,
                "entries": [],
            }

            for e in entries:
                wallet = await session.get(AgentAccount, e.wallet_id)
                agent = await session.get(User, wallet.agent_id) if wallet else None
                phase_data["entries"].append({
                    "id": str(e.id),
                    "entry_type": e.entry_type.value if hasattr(e.entry_type, "value") else str(e.entry_type),
                    "amount": float(e.amount),
                    "currency_code": e.currency_code,
                    "balance_after": float(e.balance_after),
                    "wallet_label": (
                        f"{agent.full_name if agent else '?'} — "
                        f"{wallet.payment_method_name} ({wallet.currency_code})"
                    ) if wallet else None,
                    "note": e.note,
                })
                total_entries += 1

            cat = ltx.category.value if hasattr(ltx.category, "value") else str(ltx.category)
            if cat == "TRANSACTION_IN":
                phases["collection"] = phase_data
            elif cat == "TRANSACTION_OUT":
                phases["disbursement"] = phase_data
            elif cat == "CORRECTION":
                phases["correction"] = phase_data

        return {
            "transaction_id": str(transaction_id),
            "phases": phases,
            "total_entries": total_entries,
            "collection_done": phases["collection"] is not None,
            "disbursement_done": phases["disbursement"] is not None,
            "is_reversed": phases["correction"] is not None,
        }

    # =========================================================================
    # BUSINESS — Top-up / Withdrawal manuels
    # =========================================================================

    async def topup_account(
        self,
        session: AsyncSession,
        wallet_id: UUID,
        amount: Decimal,
        currency_code: str,
        reference: str,
        description: str,
        initiated_by_id: UUID,
    ) -> LedgerEntry:
        ledger_tx = LedgerTx(
            id=uuid4(),
            reference=reference,
            category=LedgerCategory.TOP_UP,
            description=description,
            initiated_by_id=initiated_by_id,
        )
        session.add(ledger_tx)

        return await self._create_entry(
            session, wallet_id, ledger_tx.id,
            LedgerEntryType.DEBIT, amount, currency_code,
            note=description,
        )

    async def withdraw_from_account(
        self,
        session: AsyncSession,
        wallet_id: UUID,
        amount: Decimal,
        currency_code: str,
        reference: str,
        description: str,
        initiated_by_id: UUID,
    ) -> LedgerEntry:
        ledger_tx = LedgerTx(
            id=uuid4(),
            reference=reference,
            category=LedgerCategory.WITHDRAWAL,
            description=description,
            initiated_by_id=initiated_by_id,
        )
        session.add(ledger_tx)

        return await self._create_entry(
            session, wallet_id, ledger_tx.id,
            LedgerEntryType.CREDIT, amount, currency_code,
            note=description,
        )

    # =========================================================================
    # BUSINESS — Settlement
    # =========================================================================

    async def execute_settlement(
        self,
        session: AsyncSession,
        settlement: Settlement,
        executed_by_id: UUID,
    ) -> Tuple[LedgerEntry, LedgerEntry]:
        if settlement.status != SettlementStatus.APPROVED:
            raise LedgerError(f"Settlement non approuvé: {settlement.status}")

        ledger_tx = LedgerTx(
            id=uuid4(),
            reference=generate_ledger_ref("STL"),
            category=LedgerCategory.SETTLEMENT,
            description=f"Compensation {settlement.reference}: {settlement.reason}",
            exchange_rate=settlement.exchange_rate,
            initiated_by_id=executed_by_id,
        )
        session.add(ledger_tx)

        # CREDIT source
        credit_entry = await self._create_entry(
            session, settlement.from_wallet_id, ledger_tx.id,
            LedgerEntryType.CREDIT, settlement.amount,
            settlement.currency_code,
            note=f"Compensation payée {settlement.reference}",
        )

        # DEBIT destination
        target_amount = settlement.target_amount or settlement.amount
        target_currency = settlement.target_currency_code or settlement.currency_code
        debit_entry = await self._create_entry(
            session, settlement.to_wallet_id, ledger_tx.id,
            LedgerEntryType.DEBIT, target_amount, target_currency,
            note=f"Compensation reçue {settlement.reference}",
        )

        settlement.status = SettlementStatus.EXECUTED
        settlement.ledger_tx_id = ledger_tx.id
        settlement.executed_at = datetime.now(timezone.utc)
        session.add(settlement)

        return credit_entry, debit_entry

    # =========================================================================
    # AUDIT — Recalculer le solde depuis le ledger
    # =========================================================================

    async def recalculate_balance(
        self, session: AsyncSession, wallet_id: UUID,
    ) -> Decimal:
        stmt = select(
            func.coalesce(
                func.sum(
                    sa_case(
                        (LedgerEntry.entry_type == LedgerEntryType.DEBIT, LedgerEntry.amount),
                        else_=-LedgerEntry.amount,
                    )
                ), 0
            )
        ).where(LedgerEntry.wallet_id == wallet_id)

        calculated = Decimal(str((await session.execute(stmt)).scalar_one()))

        wallet = await session.get(AgentAccount, wallet_id)
        if wallet and wallet.balance != calculated:
            logger.warning(
                f"⚠️ Mismatch wallet {wallet_id}: "
                f"cache={wallet.balance}, calc={calculated}"
            )
            wallet.balance = calculated
            session.add(wallet)

        return calculated

    # =========================================================================
    # QUERY — Historique d'un wallet
    # =========================================================================

    async def get_account_history(
        self,
        session: AsyncSession,
        wallet_id: UUID,
        limit: int = 50,
        offset: int = 0,
        category: Optional[LedgerCategory] = None,
    ) -> List[LedgerEntry]:
        if category:
            stmt = (
                select(LedgerEntry)
                .join(LedgerTx, LedgerEntry.ledger_tx_id == LedgerTx.id)
                .where(LedgerEntry.wallet_id == wallet_id)
                .where(LedgerTx.category == category)
                .order_by(LedgerEntry.created_at.desc())
                .offset(offset).limit(limit)
            )
        else:
            stmt = (
                select(LedgerEntry)
                .where(LedgerEntry.wallet_id == wallet_id)
                .order_by(LedgerEntry.created_at.desc())
                .offset(offset).limit(limit)
            )
        return list((await session.execute(stmt)).scalars().all())


# Singleton
ledger_service = LedgerService()