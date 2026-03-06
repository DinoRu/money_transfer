"""
Schemas Pydantic pour le ledger.
Placer dans: src/schemas/ledger.py

Aligné sur models.py:
  - LedgerEntry: wallet_id, ledger_tx_id, note (PAS account_id/description/category)
  - LedgerTx: reference, category, description, transaction_id, initiated_by_id
  - Settlement: from_wallet_id/to_wallet_id, amount/target_amount, reason
  - AgentAccount: currency_code, payment_method_name (dénormalisés)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# AGENT ACCOUNT (table: agent_wallets)
# =============================================================================

class AgentAccountCreate(BaseModel):
    agent_id: UUID
    currency_id: UUID
    payment_method_id: UUID
    min_balance: Decimal = Field(default=Decimal("0.00"))


class AgentAccountRead(BaseModel):
    id: UUID
    agent_id: UUID
    currency_id: UUID
    currency_code: Optional[str] = None          # dénormalisé sur le model
    payment_method_id: Optional[UUID] = None
    payment_method_name: Optional[str] = None     # dénormalisé sur le model
    balance: float
    min_balance: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Enrichi par la route (pas sur le model)
    agent_name: Optional[str] = None

    class Config:
        from_attributes = True


class AgentAccountUpdate(BaseModel):
    min_balance: Optional[Decimal] = None
    is_active: Optional[bool] = None


# =============================================================================
# LEDGER ENTRY (table: ledger_entries)
#
# Champs réels du model:
#   id, ledger_tx_id, wallet_id, entry_type, amount,
#   currency_code, balance_after, note, created_at
#
# PAS sur ce model: transaction_id, category, reference,
#   description, initiated_by_id, counterpart_entry_id, settlement_id
# =============================================================================

class LedgerEntryRead(BaseModel):
    id: UUID
    ledger_tx_id: UUID                         # FK → ledger_transactions
    wallet_id: UUID                            # FK → agent_wallets
    entry_type: str                            # "DEBIT" | "CREDIT"
    amount: float
    currency_code: str
    balance_after: float
    note: Optional[str] = None                 # champ du model (pas "description")
    created_at: datetime
    # Enrichis par la route (jointure sur LedgerTx + AgentAccount)
    wallet_label: Optional[str] = None         # "Agent Name — Wave CI (XOF)"
    ledger_reference: Optional[str] = None     # LedgerTx.reference
    category: Optional[str] = None             # LedgerTx.category

    class Config:
        from_attributes = True


# =============================================================================
# TOPUP / WITHDRAWAL
# =============================================================================

class TopupRequest(BaseModel):
    wallet_id: UUID                            # était "account_id"
    amount: Decimal = Field(..., gt=0)
    description: str = Field(..., min_length=3, max_length=500)
    reference: Optional[str] = None


class WithdrawalRequest(BaseModel):
    wallet_id: UUID                            # était "account_id"
    amount: Decimal = Field(..., gt=0)
    description: str = Field(..., min_length=3, max_length=500)
    reference: Optional[str] = None


# =============================================================================
# PROCESS TRANSACTION
# =============================================================================

class ProcessTransactionRequest(BaseModel):
    transaction_id: UUID
    collection_wallet_id: UUID = Field(        # était "collection_account_id"
        ..., description="Wallet agent collecteur (pays d'envoi)"
    )
    disbursement_wallet_id: UUID = Field(      # était "disbursement_account_id"
        ..., description="Wallet agent payeur (pays de réception)"
    )
    fee_wallet_id: Optional[UUID] = Field(     # était "fee_account_id"
        None, description="Wallet pour les frais (Chapmoney Fees)"
    )


# =============================================================================
# SETTLEMENT (table: settlements)
#
# Champs réels du model:
#   id, reference, from_agent_id, from_wallet_id, to_agent_id, to_wallet_id,
#   amount, currency_code, target_amount, target_currency_code, exchange_rate,
#   status, ledger_tx_id, reason, created_by_id, approved_by_id,
#   executed_at, created_at, updated_at
# =============================================================================

class SettlementCreate(BaseModel):
    from_wallet_id: UUID                       # était "from_account_id"
    to_wallet_id: UUID                         # était "to_account_id"
    amount: Decimal = Field(..., gt=0)         # était "from_amount"
    target_amount: Optional[Decimal] = Field(  # était "to_amount"
        None, gt=0, description="Montant crédité (si cross-devise)"
    )
    target_currency_code: Optional[str] = None
    exchange_rate: Optional[Decimal] = Field(None, gt=0)
    reason: str = Field(                       # était "description"
        ..., min_length=3, max_length=500
    )


class SettlementRead(BaseModel):
    id: UUID
    reference: str
    from_agent_id: UUID
    from_wallet_id: UUID                       # était "from_account_id"
    to_agent_id: UUID
    to_wallet_id: UUID                         # était "to_account_id"
    amount: float                              # était "from_amount"
    currency_code: str                         # était "from_currency_code"
    target_amount: Optional[float] = None      # était "to_amount"
    target_currency_code: Optional[str] = None # était "to_currency_code"
    exchange_rate: Optional[float] = None
    status: str
    ledger_tx_id: Optional[UUID] = None
    reason: str                                # était "description"
    created_by_id: UUID
    approved_by_id: Optional[UUID] = None
    executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettlementApprove(BaseModel):
    proof_reference: Optional[str] = None


# =============================================================================
# DASHBOARD / STATS
# =============================================================================

class BalanceSummaryItem(BaseModel):
    currency_code: str
    currency_symbol: str
    total_balance: float
    wallets_count: int                         # était "accounts_count"
    agents_count: int


class LedgerStatsResponse(BaseModel):
    total_wallets: int                         # était "total_accounts"
    active_wallets: int                        # était "active_accounts"
    total_entries: int
    today_entries: int
    balances_by_currency: List[BalanceSummaryItem]
    pending_settlements: int