import enum
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import Index, UniqueConstraint, func, text, Enum as PgEnum

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
