"""
╔══════════════════════════════════════════════════════════════════╗
║  LEDGER API ROUTES — Endpoints admin                             ║
║  Placer dans: src/api/endpoints/v1/ledger_routes.py              ║
║  Prefix: /api/v1/admin/ledger                                    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.auth.permission import agent_or_admin_required
from src.db.models import (
    Transaction,
    TransactionStatus,
    User, Currency, PaymentType,
    AgentAccount, LedgerTx, LedgerEntry,
    LedgerEntryType, LedgerCategory,
    Settlement, SettlementStatus,
)
from src.db.session import get_session

from src.schemas.ledger import (
    AgentAccountCreate, AgentAccountRead, AgentAccountUpdate,
    LedgerEntryRead, TopupRequest, WithdrawalRequest,
    SettlementCreate, SettlementRead, SettlementApprove,
    LedgerStatsResponse, BalanceSummaryItem, ProcessTransactionRequest,
)
from src.services.ledger_service import (
    ledger_service, LedgerError, InsufficientBalanceError, AccountNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/ledger", tags=["Admin - Ledger"])


def generate_reference(prefix: str = "LED") -> str:
    ts = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    return f"{prefix}-{ts}-{uuid4().hex[:6].upper()}"


# =============================================================================
# HELPERS — Enrichir les réponses depuis le model vers le schema
# =============================================================================

async def _enrich_wallet(session: AsyncSession, acc: AgentAccount) -> dict:
    """AgentAccount model → AgentAccountRead dict (ajoute agent_name)."""
    agent = await session.get(User, acc.agent_id)
    cur = await session.get(Currency, acc.currency_id)
    pm = (
        await session.get(PaymentType, acc.payment_method_id)
        if acc.payment_method_id else None
    )
    return {
        "id": acc.id,
        "agent_id": acc.agent_id,
        "currency_id": acc.currency_id,
        "currency_code": acc.currency_code or (cur.code if cur else None),
        "payment_method_id": acc.payment_method_id,
        "payment_method_name": acc.payment_method_name or (pm.type if pm else None),
        "balance": float(acc.balance),
        "min_balance": float(acc.min_balance),
        "is_active": acc.is_active,
        "created_at": acc.created_at,
        "updated_at": acc.updated_at,
        "agent_name": agent.full_name if agent else None,
    }


async def _enrich_entry(session: AsyncSession, entry: LedgerEntry) -> dict:
    """
    LedgerEntry model → LedgerEntryRead dict.

    Le model LedgerEntry N'A PAS: category, transaction_id, reference, description.
    On les récupère via la jointure sur LedgerTx.
    """
    # Wallet label
    wallet_label = None
    wallet = await session.get(AgentAccount, entry.wallet_id)
    if wallet:
        agent = await session.get(User, wallet.agent_id)
        wallet_label = (
            f"{agent.full_name if agent else '?'} — "
            f"{wallet.payment_method_name or '?'} ({wallet.currency_code})"
        )

    # LedgerTx → reference + category
    ledger_reference = None
    category = None
    ltx = await session.get(LedgerTx, entry.ledger_tx_id)
    if ltx:
        ledger_reference = ltx.reference
        category = ltx.category.value if hasattr(ltx.category, "value") else str(ltx.category)

    return {
        "id": entry.id,
        "ledger_tx_id": entry.ledger_tx_id,
        "wallet_id": entry.wallet_id,
        "entry_type": (
            entry.entry_type.value
            if hasattr(entry.entry_type, "value")
            else str(entry.entry_type)
        ),
        "amount": float(entry.amount),
        "currency_code": entry.currency_code,
        "balance_after": float(entry.balance_after),
        "note": entry.note,
        "created_at": entry.created_at,
        # Enrichis (pas sur le model)
        "wallet_label": wallet_label,
        "ledger_reference": ledger_reference,
        "category": category,
    }


# =============================================================================
# AGENT ACCOUNTS — CRUD
# =============================================================================

@router.post("/accounts", response_model=AgentAccountRead, status_code=201)
async def create_agent_account(
    body: AgentAccountCreate,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    """Créer un wallet agent (1 par agent × devise × méthode)."""
    agent = await session.get(User, body.agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    if agent.role not in ("agent", "admin"):
        raise HTTPException(400, "L'utilisateur doit avoir le rôle 'agent' ou 'admin'")

    currency = await session.get(Currency, body.currency_id)
    if not currency:
        raise HTTPException(404, "Devise non trouvée")

    pm = await session.get(PaymentType, body.payment_method_id)
    if not pm:
        raise HTTPException(404, "Méthode de paiement non trouvée")

    # Unicité
    existing = (await session.execute(
        select(AgentAccount).where(
            AgentAccount.agent_id == body.agent_id,
            AgentAccount.currency_id == body.currency_id,
            AgentAccount.payment_method_id == body.payment_method_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Ce wallet existe déjà (id={existing.id})")

    account = AgentAccount(
        agent_id=body.agent_id,
        currency_id=body.currency_id,
        currency_code=currency.code,
        payment_method_id=body.payment_method_id,
        payment_method_name=pm.type,
        min_balance=body.min_balance,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return await _enrich_wallet(session, account)


@router.get("/accounts", response_model=List[AgentAccountRead])
async def list_agent_accounts(
    agent_id: Optional[UUID] = Query(None),
    currency_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(AgentAccount)
    if agent_id:
        stmt = stmt.where(AgentAccount.agent_id == agent_id)
    if currency_id:
        stmt = stmt.where(AgentAccount.currency_id == currency_id)
    if is_active is not None:
        stmt = stmt.where(AgentAccount.is_active == is_active)

    accounts = (await session.execute(
        stmt.order_by(AgentAccount.created_at)
    )).scalars().all()
    return [await _enrich_wallet(session, acc) for acc in accounts]


@router.get("/accounts/{wallet_id}", response_model=AgentAccountRead)
async def get_agent_account(
    wallet_id: UUID,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    acc = await session.get(AgentAccount, wallet_id)
    if not acc:
        raise HTTPException(404, "Wallet introuvable")
    return await _enrich_wallet(session, acc)


@router.patch("/accounts/{wallet_id}", response_model=AgentAccountRead)
async def update_agent_account(
    wallet_id: UUID,
    body: AgentAccountUpdate,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    acc = await session.get(AgentAccount, wallet_id)
    if not acc:
        raise HTTPException(404, "Wallet introuvable")

    update_data = body.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(acc, field, val)

    session.add(acc)
    await session.commit()
    await session.refresh(acc)
    return await _enrich_wallet(session, acc)


@router.get("/accounts/{wallet_id}/history", response_model=List[LedgerEntryRead])
async def get_wallet_history(
    wallet_id: UUID,
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    acc = await session.get(AgentAccount, wallet_id)
    if not acc:
        raise HTTPException(404, "Wallet introuvable")

    # LedgerEntry n'a PAS de champ category → on join sur LedgerTx
    if category:
        stmt = (
            select(LedgerEntry)
            .join(LedgerTx, LedgerEntry.ledger_tx_id == LedgerTx.id)
            .where(LedgerEntry.wallet_id == wallet_id)
            .where(LedgerTx.category == LedgerCategory(category))
            .order_by(LedgerEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    else:
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet_id)
            .order_by(LedgerEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

    entries = (await session.execute(stmt)).scalars().all()
    return [await _enrich_entry(session, e) for e in entries]


@router.post("/accounts/{wallet_id}/recalculate")
async def recalculate_balance(
    wallet_id: UUID,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    """Audit: recalcule le solde depuis le ledger (source of truth)."""
    acc = await session.get(AgentAccount, wallet_id)
    if not acc:
        raise HTTPException(404, "Wallet introuvable")

    try:
        calculated = await ledger_service.recalculate_balance(session, wallet_id)
        cached = acc.balance
        await session.commit()
        return {
            "wallet_id": str(wallet_id),
            "calculated_balance": float(calculated),
            "cached_balance": float(cached),
            "match": cached == calculated,
        }
    except AccountNotFoundError:
        raise HTTPException(404, "Wallet introuvable")


# =============================================================================
# TOPUP / WITHDRAWAL
# =============================================================================

@router.post("/topup", response_model=LedgerEntryRead, status_code=201)
async def topup_wallet(
    body: TopupRequest,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    try:
        acc = await session.get(AgentAccount, body.wallet_id)
        if not acc:
            raise HTTPException(404, "Wallet introuvable")

        cur = await session.get(Currency, acc.currency_id)
        entry = await ledger_service.topup_account(
            session,
            body.wallet_id,
            body.amount,
            cur.code if cur else acc.currency_code or "???",
            body.reference or generate_reference("TOP"),
            body.description,
            admin.id,
        )
        await session.commit()
        return await _enrich_entry(session, entry)
    except LedgerError as e:
        raise HTTPException(400, str(e))


@router.post("/withdraw", response_model=LedgerEntryRead, status_code=201)
async def withdraw_from_wallet(
    body: WithdrawalRequest,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    try:
        acc = await session.get(AgentAccount, body.wallet_id)
        if not acc:
            raise HTTPException(404, "Wallet introuvable")

        cur = await session.get(Currency, acc.currency_id)
        entry = await ledger_service.withdraw_from_account(
            session,
            body.wallet_id,
            body.amount,
            cur.code if cur else acc.currency_code or "???",
            body.reference or generate_reference("WTH"),
            body.description,
            admin.id,
        )
        await session.commit()
        return await _enrich_entry(session, entry)
    except InsufficientBalanceError as e:
        raise HTTPException(400, f"Solde insuffisant: {e}")
    except LedgerError as e:
        raise HTTPException(400, str(e))


# =============================================================================
# PROCESS / REVERSE TRANSACTION
# =============================================================================

@router.post("/process-transaction", response_model=List[LedgerEntryRead], status_code=201)
async def process_transaction(
    body: ProcessTransactionRequest,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    """Traiter une transaction client dans le ledger."""
    tx = await session.get(Transaction, body.transaction_id)
    if not tx:
        raise HTTPException(404, "Transaction introuvable")
    if tx.status not in (TransactionStatus.FUNDS_DEPOSITED, TransactionStatus.IN_PROGRESS):
        raise HTTPException(400, f"Non traitable: statut={tx.status.value}")

    # Anti-doublon via LedgerTx.transaction_id (PAS LedgerEntry qui n'a pas ce champ)
    existing_ltx = (await session.execute(
        select(LedgerTx).where(
            LedgerTx.transaction_id == tx.id,
            LedgerTx.category == LedgerCategory.TRANSACTION_IN,
        )
    )).scalar_one_or_none()
    if existing_ltx:
        raise HTTPException(409, f"Déjà traitée dans le ledger: {existing_ltx.reference}")

    try:
        entries = await ledger_service.process_transaction(
            session, tx,
            body.collection_wallet_id,
            body.disbursement_wallet_id,
            body.fee_wallet_id,
        )
        await session.commit()
        return [await _enrich_entry(session, e) for e in entries]
    except LedgerError as e:
        await session.rollback()
        raise HTTPException(400, str(e))


@router.post("/reverse-transaction/{transaction_id}", response_model=List[LedgerEntryRead])
async def reverse_transaction(
    transaction_id: UUID,
    reason: str = Query(..., min_length=5),
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    tx = await session.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(404, "Transaction introuvable")
    try:
        entries = await ledger_service.reverse_transaction(session, tx, reason, admin.id)
        await session.commit()
        return [await _enrich_entry(session, e) for e in entries]
    except LedgerError as e:
        await session.rollback()
        raise HTTPException(400, str(e))


# =============================================================================
# SETTLEMENTS
# =============================================================================

@router.post("/settlements", response_model=SettlementRead, status_code=201)
async def create_settlement(
    body: SettlementCreate,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    from_wallet = await session.get(AgentAccount, body.from_wallet_id)
    if not from_wallet:
        raise HTTPException(404, "Wallet source introuvable")
    to_wallet = await session.get(AgentAccount, body.to_wallet_id)
    if not to_wallet:
        raise HTTPException(404, "Wallet destination introuvable")

    settlement = Settlement(
        reference=generate_reference("STL"),
        from_agent_id=from_wallet.agent_id,
        from_wallet_id=from_wallet.id,
        to_agent_id=to_wallet.agent_id,
        to_wallet_id=to_wallet.id,
        amount=body.amount,
        currency_code=from_wallet.currency_code,
        target_amount=body.target_amount,
        target_currency_code=body.target_currency_code or to_wallet.currency_code,
        exchange_rate=body.exchange_rate,
        status=SettlementStatus.PENDING,
        reason=body.reason,
        created_by_id=admin.id,
    )
    session.add(settlement)
    await session.commit()
    await session.refresh(settlement)
    return settlement


@router.get("/settlements", response_model=List[SettlementRead])
async def list_settlements(
    settlement_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Settlement)
    if settlement_status:
        stmt = stmt.where(Settlement.status == SettlementStatus(settlement_status))
    results = (await session.execute(
        stmt.order_by(Settlement.created_at.desc()).limit(limit)
    )).scalars().all()
    return list(results)


@router.post("/settlements/{settlement_id}/approve", response_model=SettlementRead)
async def approve_settlement(
    settlement_id: UUID,
    body: SettlementApprove,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    s = await session.get(Settlement, settlement_id)
    if not s:
        raise HTTPException(404, "Settlement introuvable")
    if s.status != SettlementStatus.PENDING:
        raise HTTPException(400, f"Non approuvable: {s.status.value}")

    s.status = SettlementStatus.APPROVED
    s.approved_by_id = admin.id
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@router.post("/settlements/{settlement_id}/execute")
async def execute_settlement(
    settlement_id: UUID,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    s = await session.get(Settlement, settlement_id)
    if not s:
        raise HTTPException(404, "Settlement introuvable")
    try:
        cr, dr = await ledger_service.execute_settlement(session, s, admin.id)
        await session.commit()
        return {"status": "EXECUTED", "credit": str(cr.id), "debit": str(dr.id)}
    except LedgerError as e:
        await session.rollback()
        raise HTTPException(400, str(e))


@router.post("/settlements/{settlement_id}/cancel", response_model=SettlementRead)
async def cancel_settlement(
    settlement_id: UUID,
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    s = await session.get(Settlement, settlement_id)
    if not s:
        raise HTTPException(404, "Settlement introuvable")
    if s.status in (SettlementStatus.EXECUTED, SettlementStatus.CANCELLED):
        raise HTTPException(400, f"Non annulable: {s.status.value}")

    s.status = SettlementStatus.CANCELLED
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


# =============================================================================
# DASHBOARD / STATS
# =============================================================================

@router.get("/stats", response_model=LedgerStatsResponse)
async def get_ledger_stats(
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    total_wallets = (await session.execute(
        select(func.count(AgentAccount.id))
    )).scalar_one()

    active_wallets = (await session.execute(
        select(func.count(AgentAccount.id)).where(AgentAccount.is_active == True)
    )).scalar_one()

    total_entries = (await session.execute(
        select(func.count(LedgerEntry.id))
    )).scalar_one()

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_entries = (await session.execute(
        select(func.count(LedgerEntry.id)).where(LedgerEntry.created_at >= today)
    )).scalar_one()

    pending = (await session.execute(
        select(func.count(Settlement.id)).where(
            Settlement.status.in_([SettlementStatus.PENDING, SettlementStatus.APPROVED])
        )
    )).scalar_one()

    # Grouper par currency_code (champ dénormalisé sur AgentAccount)
    bal_rows = (await session.execute(
        select(
            AgentAccount.currency_code,
            func.sum(AgentAccount.balance).label("total"),
            func.count(AgentAccount.id).label("wallets_count"),
            func.count(func.distinct(AgentAccount.agent_id)).label("agents_count"),
        ).where(AgentAccount.is_active == True)
        .group_by(AgentAccount.currency_code)
    )).all()

    # Lookup symbols
    currencies = {
        c.code: c.symbol
        for c in (await session.execute(select(Currency))).scalars().all()
    }

    balances = [
        BalanceSummaryItem(
            currency_code=row.currency_code or "?",
            currency_symbol=currencies.get(row.currency_code or "", "?"),
            total_balance=float(row.total or 0),
            wallets_count=row.wallets_count,
            agents_count=row.agents_count,
        )
        for row in bal_rows
    ]

    return LedgerStatsResponse(
        total_wallets=total_wallets,
        active_wallets=active_wallets,
        total_entries=total_entries,
        today_entries=today_entries,
        balances_by_currency=balances,
        pending_settlements=pending,
    )


@router.get("/entries", response_model=List[LedgerEntryRead])
async def get_global_entries(
    category: Optional[str] = Query(None),
    transaction_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: User = Depends(agent_or_admin_required),
    session: AsyncSession = Depends(get_session),
):
    """
    Journal comptable global.

    LedgerEntry n'a PAS category ni transaction_id →
    on join sur LedgerTx pour filtrer.
    """
    stmt = (
        select(LedgerEntry)
        .join(LedgerTx, LedgerEntry.ledger_tx_id == LedgerTx.id)
        .order_by(LedgerEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if category:
        stmt = stmt.where(LedgerTx.category == LedgerCategory(category))
    if transaction_id:
        stmt = stmt.where(LedgerTx.transaction_id == transaction_id)

    entries = (await session.execute(stmt)).scalars().all()
    return [await _enrich_entry(session, e) for e in entries]