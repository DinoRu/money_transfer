import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (Index, UniqueConstraint, func, text, Enum as PgEnum, CheckConstraint, DateTime, Numeric)

from sqlmodel import SQLModel, Field, Column, DECIMAL, Relationship
import sqlalchemy.dialects.postgresql as pg



class UserRole(str, Enum):
    ADMIN = 'admin'
    USER = 'user'
    AGENT = 'agent'


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, primary_key=True, default=uuid.uuid4))
    full_name: str = Field(sa_column=Column(pg.VARCHAR))
    phone: str = Field(sa_column=Column(pg.VARCHAR, unique=True))
    email: str = Field(sa_column=Column(pg.VARCHAR, unique=True))

    country: str = Field(sa_column=Column(pg.VARCHAR, nullable=False))

    hash_password: str = Field(sa_column=Column(pg.VARCHAR, nullable=False), exclude=True)

    role: UserRole = Field(default=UserRole.USER, sa_column=Column(pg.VARCHAR, nullable=False))
    profile_picture_url: Optional[str] = Field(sa_column=Column(pg.VARCHAR, nullable=True))

    token: "FCMToken" = Relationship(back_populates='user', cascade_delete=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow))

    token: "FCMToken" = Relationship(back_populates='user', cascade_delete=True)
    # Transactions envoyées
    sent_transactions: List["Transaction"] = Relationship(
        back_populates="sender",
        sa_relationship_kwargs={"foreign_keys": "[Transaction.sender_id]"},
    )

    # Transactions traitées (admin)
    processed_transactions: List["Transaction"] = Relationship(
        back_populates="processed_by",
        sa_relationship_kwargs={"foreign_keys": "[Transaction.processed_by_admin_id]"},
    )


class Currency(SQLModel, table=True):
    __tablename__ = "currencies"
    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    code: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))
    name: str = Field(sa_column=Column(pg.VARCHAR, nullable=False))
    symbol: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))

    countries: List["Country"] = Relationship(back_populates='currency')


class Country(SQLModel, table=True):
    __tablename__ = 'countries'
    id:uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    name: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))
    code_iso: str = Field(sa_column=Column(pg.VARCHAR(2), nullable=False, unique=True))
    currency_id: uuid.UUID = Field(foreign_key='currencies.id', nullable=False)
    dial_code: str = Field(sa_column=Column(pg.VARCHAR(4)))
    phone_pattern: str = Field(sa_column=Column(pg.VARCHAR))
    can_send: bool = Field(
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default='true'),
        description="Détermine si le pays peut envoyer de l'argent"
    )
    currency: "Currency" = Relationship(back_populates='countries')
    payment_types: List["PaymentType"] = Relationship(back_populates="country", cascade_delete=True)
    receiving_types: List["ReceivingType"] = Relationship(back_populates="country", cascade_delete=True)


class Rate(SQLModel, table=True):
    __tablename__ = "rates"
    __table_args__ = (Index('idx_rate', 'rate'), )
    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    currency: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, index=True))
    rate: Decimal = Field(sa_column=Column(DECIMAL(precision=10, scale=2), nullable=False))


class ReceivingType(SQLModel, table=True):
    __tablename__ = "receiving_type"
    __table_args__ = (Index('idx_receiving_type', 'type'),)
    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    type: str = Field(sa_column=Column(pg.VARCHAR, nullable=False))
    country_id: uuid.UUID = Field(foreign_key='countries.id')

    country: "Country" = Relationship(back_populates="receiving_types")


class PaymentType(SQLModel, table=True):
    __tablename__ = "payment_type"
    __table_args__ = (Index('idx_payment_type', 'type'),)

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    type: str = Field(sa_column=Column(pg.VARCHAR(50), nullable=False))
    owner_full_name: str = Field(sa_column=Column(pg.VARCHAR(50), nullable=False))
    phone_number: str | None = Field(sa_column=Column(pg.VARCHAR(20), default=None))
    account_number: str | None = Field(sa_column=Column(pg.VARCHAR(20), default=None))
    country_id: uuid.UUID = Field(foreign_key="countries.id")
    country: "Country" = Relationship(back_populates="payment_types")


class TransactionStatus(str, Enum):
    """
    Flow: FUNDS_DEPOSITED → IN_PROGRESS → COMPLETED
    
    FUNDS_DEPOSITED = User a confirmé avoir déposé les fonds
    IN_PROGRESS     = Admin a vérifié, transfert en cours
    COMPLETED       = Destinataire a reçu l'argent
    EXPIRED         = Timer expiré (jamais créé en DB normalement)
    CANCELLED       = Annulée par user ou admin
    """
    FUNDS_DEPOSITED = "FUNDS_DEPOSITED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"



def generate_reference():
    return f"tx{uuid.uuid4().hex[:10].lower()}"

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    __table_args__ = (Index("idx_transaction_status", "status"), )

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    timestamp: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.now))
    
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )

    updated_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )
    reference: str = Field(sa_column=Column(pg.VARCHAR(12), unique=True), default_factory=generate_reference)
    sender_id: uuid.UUID = Field(foreign_key="users.id")
    sender_country: str = Field(sa_column=Column(pg.VARCHAR(50), nullable=False))
    sender_currency: str = Field(sa_column=Column(pg.VARCHAR(10), nullable=False))
    sender_amount: int = Field(sa_column=Column(pg.INTEGER))
    receiver_country: str = Field(sa_column=Column(pg.VARCHAR(50)))
    receiver_currency: str = Field(sa_column=Column(pg.VARCHAR(10)))
    receiver_amount: int = Field(sa_column=Column(pg.INTEGER))
    conversion_rate: Decimal = Field(sa_column=Column(DECIMAL(precision=10, scale=2)))
    payment_method: str = Field(sa_column=Column(pg.VARCHAR(50)))
    recipient_name: str = Field(sa_column=Column(pg.VARCHAR(50)))
    recipient_phone: str = Field(sa_column=Column(pg.VARCHAR(50)))
    receiving_method: str = Field(sa_column=Column(pg.VARCHAR(50)))
    include_fee: bool = Field(sa_column=Column(pg.BOOLEAN, default=False))
    fee_amount: int = Field(sa_column=Column(pg.INTEGER, nullable=False, default=0))
    status: TransactionStatus = Field(
        sa_column=Column(
            PgEnum(TransactionStatus, name="transaction_status", create_type=False),
            nullable=False,
            default=TransactionStatus.FUNDS_DEPOSITED,
        )
    )

    processed_at: datetime | None = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True)
    )

    completed_at: datetime | None = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True)
    )

    cancelled_at: datetime | None = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True)
    )

    expired_at: datetime | None = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True)
    )

    processed_by_admin_id: uuid.UUID | None = Field(
        foreign_key="users.id",
        nullable=True
    )
    
    # Relations
    sender: "User" = Relationship(
        back_populates="sent_transactions",
        sa_relationship_kwargs={"foreign_keys": "[Transaction.sender_id]"},
    )

    processed_by: Optional["User"] = Relationship(
        back_populates="processed_transactions",
        sa_relationship_kwargs={"foreign_keys": "[Transaction.processed_by_admin_id]"},
    )


class Fee(SQLModel, table=True):
    __tablename__ = 'fees'
    __table_args__ = (Index('idx_from_to', 'from_country_id', 'to_country_id'),)

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    from_country_id: uuid.UUID = Field(foreign_key='countries.id', nullable=False, ondelete='CASCADE')
    to_country_id: uuid.UUID = Field(foreign_key='countries.id', nullable=False, ondelete='CASCADE')
    fee: Decimal = Field(sa_column=Column(DECIMAL(precision=10, scale=2), nullable=False))
     # =========================
    # TIMESTAMPS
    # =========================
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()")
        )
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
            onupdate=datetime.utcnow
        )
    )


class FCMToken(SQLModel, table=True):
    __tablename__ = "fcm_tokens"

    pk: uuid.UUID = Field(sa_column=Column(pg.UUID, primary_key=True, default=uuid.uuid4))
    token: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))
    user_id: uuid.UUID = Field(foreign_key='users.id')

    user: User = Relationship(back_populates='token')



class ExchangeRates(SQLModel, table=True):
    __tablename__ = "ex_rates"
    __table_args__ = (
        Index("idx_from_to_currency", "from_currency_id", "to_currency_id"),
        UniqueConstraint('from_currency_id', 'to_currency_id', name='unique_currency_pair'),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(pg.UUID, primary_key=True))
    from_currency_id: uuid.UUID = Field(foreign_key='currencies.id', nullable=False)
    to_currency_id: uuid.UUID = Field(foreign_key='currencies.id', nullable=False)
    rate: Decimal = Field(sa_column=Column(DECIMAL, nullable=False))

    from_currency: Currency = Relationship(sa_relationship_kwargs={'foreign_keys': "[ExchangeRates.from_currency_id]"})
    to_currency: Currency = Relationship(sa_relationship_kwargs={"foreign_keys": "[ExchangeRates.to_currency_id]"})
    
    
class TransactionStatusHistory(SQLModel, table=True):
    __tablename__ = "transaction_status_history"

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID, primary_key=True, default=uuid.uuid4)
    )

    transaction_id: uuid.UUID = Field(
        foreign_key="transactions.id",
        nullable=False
    )

    old_status: TransactionStatus = Field(
        sa_column=Column(pg.VARCHAR(20), nullable=False)
    )

    new_status: TransactionStatus = Field(
        sa_column=Column(pg.VARCHAR(20), nullable=False)
    )

    changed_by_admin_id: uuid.UUID | None = Field(
        foreign_key="users.id",
        nullable=True
    )

    reason: str | None = Field(
        sa_column=Column(pg.VARCHAR(255), nullable=True)
    )

    changed_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )



# =============================================================================
# ENUMS
# =============================================================================

class LedgerEntryType(str, enum.Enum):
    """Type d'écriture comptable"""
    DEBIT = "DEBIT"     # Augmente le solde (agent reçoit des fonds)
    CREDIT = "CREDIT"   # Diminue le solde (agent décaisse des fonds)


class LedgerCategory(str, enum.Enum):
    """Catégorie de l'opération — pour reporting"""
    TRANSACTION_IN = "TRANSACTION_IN"       # Dépôt client → agent pays envoi
    TRANSACTION_OUT = "TRANSACTION_OUT"     # Agent pays réception → bénéficiaire
    FEE_COLLECTED = "FEE_COLLECTED"         # Frais collectés
    SETTLEMENT = "SETTLEMENT"               # Compensation entre agents
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT" # Ajustement manuel admin
    TOP_UP = "TOP_UP"                       # Recharge de solde agent
    WITHDRAWAL = "WITHDRAWAL"               # Retrait de solde agent
    CORRECTION = "CORRECTION"               # Correction d'erreur


class SettlementStatus(str, enum.Enum):
    """Statut d'un settlement"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


# =============================================================================
# AGENT WALLET — Solde dénormalisé par agent / devise / méthode
# =============================================================================

class AgentAccount(SQLModel, table=True):
    """
    Solde d'un agent pour une devise et méthode de paiement donnée.
    
    Exemples:
    - Agent Abidjan / XOF / Wave         → solde: 2,500,000 XOF
    - Agent Abidjan / XOF / Orange Money  → solde: 1,200,000 XOF
    - Agent Moscou  / RUB / Sberbank      → solde:   450,000 RUB
    
    Le solde est dénormalisé pour la performance.
    La source de vérité reste le ledger (somme des écritures).
    """
    __tablename__ = "agent_wallets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Quel agent ?
    agent_id: UUID = Field(foreign_key="users.id", index=True)

    # Quelle devise ?
    currency_id: UUID = Field(foreign_key="currencies.id", index=True)
    currency_code: str = Field(max_length=3)  # Dénormalisé pour requêtes rapides

    # Quelle méthode de paiement ? (None = solde global devise)
    payment_method_id: Optional[UUID] = Field(
        default=None, foreign_key="payment_type.id", index=True
    )
    payment_method_name: Optional[str] = Field(default=None, max_length=100)

    # Solde actuel (dénormalisé, mis à jour atomiquement)
    balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(18, 2), nullable=False, server_default="0.00")
    )

    # Solde minimum autorisé (négatif = découvert autorisé)
    min_balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(18, 2), nullable=False, server_default="0.00")
    )

    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now()
        )
    )

    # Relations
    # agent: Optional["User"] = Relationship()
    ledger_entries: List["LedgerEntry"] = Relationship(back_populates="wallet")

    __table_args__ = (
        # Un seul wallet par combinaison agent/devise/méthode
        Index(
            "uq_agent_currency_method",
            "agent_id", "currency_id", "payment_method_id",
            unique=True
        ),
    )

    def can_debit(self, amount: Decimal) -> bool:
        """Vérifie si le wallet peut supporter un débit (sortie de fonds)"""
        return (self.balance - amount) >= self.min_balance


# =============================================================================
# LEDGER TX — Transaction comptable (regroupe les écritures)
# =============================================================================

class LedgerTx(SQLModel, table=True):
    """
    Transaction comptable = groupe d'écritures qui doivent s'équilibrer.
    
    Exemple pour: Client CI envoie 100,000 XOF → Russie (13,500 RUB):
    
    LedgerTx "LDG-2025-00042":
      ├─ DEBIT  Wallet(AgentAbidjan/XOF/Wave)    +100,000 XOF
      ├─ CREDIT Wallet(AgentMoscou/RUB/Sberbank)  -13,500 RUB
      └─ DEBIT  Wallet(System/XOF/Fees)             +5,000 XOF
    """
    __tablename__ = "ledger_transactions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Référence unique lisible
    reference: str = Field(max_length=50, index=True, unique=True)

    # Lien vers la transaction client (None pour settlements/ajustements)
    transaction_id: Optional[UUID] = Field(
        default=None, foreign_key="transactions.id", index=True
    )

    # Catégorie
    category: LedgerCategory = Field(
        sa_column=Column(
            PgEnum(LedgerCategory, name="ledger_category"),
            nullable=False
        )
    )

    # Description lisible
    description: str = Field(max_length=500)

    # Taux de change appliqué (si multi-devises)
    exchange_rate: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(12, 6))
    )

    # Qui a initié ? (admin pour ajustements manuels)
    initiated_by_id: Optional[UUID] = Field(
        default=None, foreign_key="users.id"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    # Relations
    entries: List["LedgerEntry"] = Relationship(back_populates="ledger_tx")


# =============================================================================
# LEDGER ENTRY — Écriture comptable unitaire (IMMUTABLE)
# =============================================================================

class LedgerEntry(SQLModel, table=True):
    """
    Écriture comptable unitaire — JAMAIS modifiée ni supprimée.
    
    Règles:
    - amount est TOUJOURS positif
    - entry_type détermine le sens:
        DEBIT  = +solde (l'agent reçoit)
        CREDIT = -solde (l'agent décaisse)
    - balance_after = snapshot du solde immédiatement après cette écriture
    - Pour corriger: créer une écriture inverse, jamais modifier
    """
    __tablename__ = "ledger_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # À quelle transaction comptable ?
    ledger_tx_id: UUID = Field(foreign_key="ledger_transactions.id", index=True)

    # Quel wallet impacté ?
    wallet_id: UUID = Field(foreign_key="agent_wallets.id", index=True)

    # DEBIT ou CREDIT
    entry_type: LedgerEntryType = Field(
        sa_column=Column(
            PgEnum(LedgerEntryType, name="ledger_entry_type"),
            nullable=False
        )
    )

    # Montant (TOUJOURS positif)
    amount: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False)
    )

    # Devise (dénormalisé)
    currency_code: str = Field(max_length=3)

    # Solde du wallet APRÈS cette écriture (piste d'audit)
    balance_after: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False)
    )

    # Note optionnelle
    note: Optional[str] = Field(default=None, max_length=500)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    # Relations
    ledger_tx: Optional[LedgerTx] = Relationship(back_populates="entries")
    wallet: Optional[AgentAccount] = Relationship(back_populates="ledger_entries")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ledger_amount_positive"),
        Index("ix_ledger_wallet_created", "wallet_id", "created_at"),
        Index("ix_ledger_tx_type", "ledger_tx_id", "entry_type"),
    )


# =============================================================================
# SETTLEMENT — Compensation entre agents
# =============================================================================

class Settlement(SQLModel, table=True):
    """
    Compensation / rééquyhule trop de fonds et un autre en manque,
    l'admin crée un settlement pour rééquilibrer.
    
    Flow: PENDING → APPROVED → EXECUTED (crée les écritures ledger)
    """
    __tablename__ = "settlements"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    reference: str = Field(max_length=50, index=True, unique=True)

    # Agent source (celui qui paie / réduit son solde)
    from_agent_id: UUID = Field(foreign_key="users.id", index=True)
    from_wallet_id: UUID = Field(foreign_key="agent_wallets.id")

    # Agent destination (celui qui reçoit)
    to_agent_id: UUID = Field(foreign_key="users.id", index=True)
    to_wallet_id: UUID = Field(foreign_key="agent_wallets.id")

    # Montant source
    amount: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False)
    )
    currency_code: str = Field(max_length=3)

    # Si cross-currency (ex: XOF → RUB)
    target_amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(18, 2))
    )
    target_currency_code: Optional[str] = Field(default=None, max_length=3)
    exchange_rate: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(12, 6))
    )

    # Statut
    status: SettlementStatus = Field(
        default=SettlementStatus.PENDING,
        sa_column=Column(
            PgEnum(SettlementStatus, name="settlement_status"),
            nullable=False,
            server_default="PENDING"
        )
    )

    # Lien vers l'écriture comptable (créé à l'exécution)
    ledger_tx_id: Optional[UUID] = Field(
        default=None, foreign_key="ledger_transactions.id"
    )

    # Metadata
    reason: str = Field(max_length=500)
    created_by_id: UUID = Field(foreign_key="users.id")
    approved_by_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    executed_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now()
        )
    )
