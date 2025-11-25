import enum
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import SQLModel, Field, Column, DECIMAL, Relationship
import sqlalchemy.dialects.postgresql as pg

class UserRole(str, Enum):
    ADMIN = 'admin'
    USER = 'user'
    AGENT = 'agent'
    


class PaymentPartnerType(str, enum.Enum):
    """Types de méthodes de paiement"""
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    CASH_PICKUP = "cash_pickup"
    CARD = "card"
    

class FeeType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"



class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, primary_key=True, default=uuid.uuid4))
    full_name: str = Field(sa_column=Column(pg.VARCHAR))
    phone: str = Field(sa_column=Column(pg.VARCHAR, unique=True))
    email: str = Field(sa_column=Column(pg.VARCHAR, unique=True, nullable=False), description="Adresse e-mail de l'utilisateur")

    hash_password: str = Field(sa_column=Column(pg.VARCHAR, nullable=False), exclude=True)

    role: UserRole = Field(default=UserRole.USER, sa_column=Column(pg.VARCHAR, nullable=False))
    profile_picture_url: Optional[str] = Field(sa_column=Column(pg.VARCHAR, nullable=True))

    token: "FCMToken" = Relationship(back_populates='user', cascade_delete=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow))

    token: "FCMToken" = Relationship(back_populates='user', cascade_delete=True)
    transactions: List["Transaction"] = Relationship(back_populates='sender', cascade_delete=True)
    
    def __repr__(self):
        return f"User(id={self.id}, full_name={self.full_name}, email={self.email}, role={self.role})"
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    @property
    def is_agent(self) -> bool:
        return self.role == UserRole.AGENT
    


class Currency(SQLModel, table=True):
    __tablename__ = "currencies"
    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    code: str = Field(sa_column=Column(pg.VARCHAR, nullable=False), description="Code ISO de la monnaie, ex: USD, EUR")
    name: str = Field(sa_column=Column(pg.VARCHAR, nullable=False))
    symbol: str = Field(sa_column=Column(pg.VARCHAR, nullable=False), description="Symbole de la monnaie, ex: $, €")
    description: str | None = Field(sa_column=Column(pg.VARCHAR, default=None)) 
    is_active: bool = Field(sa_column=Column(pg.BOOLEAN, nullable=False, default=True))
    countries: List["Country"] = Relationship(back_populates="currency", cascade_delete=True)
    
    exchange_rates_from: List["ExchangeRates"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[ExchangeRates.from_currency_id]"}, back_populates="from_currency")
    exchange_rates_to: List["ExchangeRates"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[ExchangeRates.to_currency_id]"}, back_populates="to_currency")
    
    def __repr__(self):
        return f"Currency(code={self.code}, name={self.name}, symbol={self.symbol})"
    
    @property
    def display_name(self) -> str:
        return f"({self.code}) {self.name}"
    

class Country(SQLModel, table=True):
    __tablename__ = 'countries'
    
    id:uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    name: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))
    currency_id: uuid.UUID = Field(foreign_key='currencies.id', nullable=False)
    dial_code: str = Field(sa_column=Column(pg.VARCHAR(4)))
    flag: str = Field(sa_column=Column(pg.VARCHAR, nullable=False), description="Emoji du drapeau du pays")
    phone_number_length: int = Field(sa_column=Column(pg.INTEGER, nullable=False, default=9), description="Longueur du numéro de téléphone pour ce pays" )
    phone_format_example: str = Field(sa_column=Column(pg.VARCHAR(20), nullable=True), description="Exemple de format de numéro de téléphone pour ce pays")
    can_send_from: bool = Field(
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default='true'),
        description="Détermine si le pays peut envoyer de l'argent"
    )
    can_send_to: bool = Field(
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default='true'),
        description="Détermine si le pays peut recevoir de l'argent"
    )
    currency: "Currency" = Relationship(back_populates='countries')
    payment_partners: List["PaymentPartner"] = Relationship(back_populates="country", cascade_delete=True)
    
    fees_from: List["Fee"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Fee.from_country_id]"}, back_populates="from_country")
    fees_to: List["Fee"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Fee.to_country_id]"}, back_populates="to_country")
    
    def __repr__(self):
        return f"Country(name={self.name}, currency_id={self.currency_id})"
    
    @property
    def display_name(self) -> str:
        return f"{self.flag} ({self.name})"
    
    @property
    def currency_code(self) -> str:
       return self.currency.code
   
    @property
    def phone_code(self) -> str:
        """Code téléphonique du pays avec le préfixe + """
        return self.dial_code
    
    @property
    def numeric_phone_code(self) -> str:
        """Code téléphonique du pays sans le préfixe + """
        return self.dial_code.lstrip('+')  
 
 
class PaymentPartner(SQLModel, table=True):
    __tablename__ = "payment_partners"
    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    name: str = Field(sa_column=Column(pg.VARCHAR(100), nullable=False, unique=True))
    country_id: uuid.UUID = Field(foreign_key="countries.id")
    type: PaymentPartnerType = Field(sa_column=Column(pg.VARCHAR(50), nullable=False))
    country: "Country" = Relationship(back_populates="payment_partners")
    description: str | None = Field(sa_column=Column(pg.VARCHAR(255), default=None))
    is_active: bool = Field(sa_column=Column(pg.BOOLEAN, nullable=False, default=True))
    can_send: bool = Field(
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default='true'),
        description="Détermine si le partenaire peut être utilisé pour envoyer de l'argent")
    can_receive: bool = Field(
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default='true'),
        description="Détermine si le partenaire peut être utilisé pour recevoir de l'argent")
    # Relationship back to Country
    country: "Country" = Relationship(back_populates="payment_partners")
    payment_accounts: List["PaymentAccount"] = Relationship(back_populates="payment_partner", cascade_delete=True)
    
    

class PaymentAccount(SQLModel, table=True):
    __tablename__ = "payment_accounts"

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    payment_partner_id: uuid.UUID = Field(foreign_key="payment_partners.id")
    account_name: str = Field(sa_column=Column(pg.VARCHAR(100), nullable=False), description="Nom du compte")
    account_number: str | None = Field(sa_column=Column(pg.VARCHAR(20), default=None))
    bank_name: str | None = Field(sa_column=Column(pg.VARCHAR(100), default=None))
    is_active: bool = Field(sa_column=Column(pg.BOOLEAN, nullable=False, default=True), description="Détermine si le compte est actif")
    payment_partner: "PaymentPartner" = Relationship(back_populates="payment_accounts")
    
    def __repr__(self):
        return f"PaymentAccount(id={self.id}, payment_partner_id={self.payment_partner_id}, account_name={self.account_name})"
    
    @property
    def is_valid(self) -> bool:
        """Vérifie si le compte de paiement a les informations nécessaires en fonction du type de partenaire de paiement."""
        if not self.is_active:
            return False
        # Ajouter d'autres types de validation selon les besoins
        return True
    

class TransactionStatus(str, Enum):
    AWAITING_PAYMENT = "En attente de paiement"
    COMPLETED = "Effectuée"
    FOUNDS_DEPOSITED = 'Dépôt confirmé'
    EXPIRED = "Expirée"
    CANCELLED = "Annulée"


def generate_reference():
    return f"RTX{uuid.uuid4().hex[:10].lower()}"

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    __table_args__ = (Index("idx_transaction_status", "status"), )

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    timestamp: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.now))
    reference: str = Field(sa_column=Column(pg.VARCHAR(12), unique=True), default_factory=generate_reference)
    
    # Informations geographiques
    sender_country_id: uuid.UUID = Field(foreign_key="countries.id")
    receiver_country_id: uuid.UUID = Field(foreign_key="countries.id")
    sender_partner_id: uuid.UUID = Field(foreign_key="payment_partners.id")
    receiver_partner_id: uuid.UUID = Field(foreign_key="payment_partners.id")
    
    # Informations sur l'expéditeur et le destinataire
    sender_id: uuid.UUID = Field(foreign_key="users.id")
    receiver_full_name: str = Field(sa_column=Column(pg.VARCHAR(100), nullable=False))
    receiver_phone: str = Field(sa_column=Column(pg.VARCHAR(20), nullable=False))
    receiver_email: str = Field(sa_column=Column(pg.VARCHAR(100), nullable=True))
    
    # Montants et taux
    sender_amount: Decimal = Field(sa_column=Column(DECIMAL(precision=15, scale=0), nullable=False))
    sender_currency: str = Field(sa_column=Column(pg.VARCHAR(10), nullable=False))
    receiver_amount: Decimal = Field(sa_column=Column(DECIMAL(precision=15, scale=0), nullable=False))
    receiver_currency: str = Field(sa_column=Column(pg.VARCHAR(10)))
    exchange_rate: Decimal = Field(sa_column=Column(DECIMAL(precision=10, scale=4), nullable=False))
    
    # Frais (calculés à partir du modèle Fee)
    applied_fee: Decimal = Field(sa_column=Column(DECIMAL(precision=10, scale=2), nullable=False, default=0))
    total_to_pay: Decimal = Field(sa_column=Column(DECIMAL(precision=15, scale=0), nullable=False))
    
    # Statut et suivi
    status: TransactionStatus = Field(sa_column=Column(pg.VARCHAR(20), nullable=False), default=TransactionStatus.AWAITING_PAYMENT)
    notes: str | None = Field(sa_column=Column(pg.VARCHAR(255), default=None))
    paid_at: datetime | None = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=None))
    completed_at: datetime | None = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=None))
    cancelled_at: datetime | None = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=None))
    expired_at: datetime | None = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), default=None))
    
    # Metadonnées supplémentaires
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column=Column(pg.TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow))
    
    # Relations
    sender_country: "Country" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Transaction.sender_country_id]"})
    receiver_country: "Country" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Transaction.receiver_country_id]"})
    sender_partner: "PaymentPartner" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Transaction.sender_partner_id]"})
    receiver_partner: "PaymentPartner" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Transaction.receiver_partner_id]"})
    sender: "User" = Relationship(back_populates='transactions')


class Fee(SQLModel, table=True):
    __tablename__ = 'fees'
    __table_args__ = (Index('idx_from_to', 'from_country_id', 'to_country_id'),)

    id: uuid.UUID = Field(sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4))
    from_country_id: uuid.UUID = Field(foreign_key='countries.id', nullable=False, ondelete='CASCADE')
    to_country_id: uuid.UUID = Field(foreign_key='countries.id', nullable=False, ondelete='CASCADE')
    
    # Types de frais
    fee_type: FeeType = Field(sa_column=Column(pg.VARCHAR(20), nullable=False))
    fee_value: Decimal = Field(sa_column=Column(DECIMAL(precision=10, scale=2), nullable=False))
    # Applicabilité
    min_amount: Decimal = Field(sa_column=Column(DECIMAL(precision=15, scale=2), default=0))
    max_amount: Decimal | None = Field(sa_column=Column(DECIMAL(precision=15, scale=2), default=None))
    # Métadonnées
    is_active: bool = Field(sa_column=Column(pg.BOOLEAN, nullable=False, default=True))
    # Relations
    from_country: "Country" = Relationship(
    back_populates="fees_from",
    sa_relationship_kwargs={"foreign_keys": "[Fee.from_country_id]"}
)

    to_country: "Country" = Relationship(
        back_populates="fees_to",
        sa_relationship_kwargs={"foreign_keys": "[Fee.to_country_id]"}
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
    
    updated_by_user_id: uuid.UUID = Field(foreign_key='users.id', nullable=True, description="ID de l'utilisateur qui a mis à jour le taux")

    from_currency: Currency = Relationship(sa_relationship_kwargs={"foreign_keys": "[ExchangeRates.from_currency_id]"}, back_populates="exchange_rates_from")
    to_currency: Currency = Relationship(sa_relationship_kwargs={"foreign_keys": "[ExchangeRates.to_currency_id]"}, back_populates="exchange_rates_to")
    
    
    def __repr__(self):
        return f"ExchangeRates(from_currency_id={self.from_currency.code}, to_currency_id={self.to_currency.code}, rate={self.rate})"
    
    def calculate_exchanged_amount(self, amount: Decimal) -> Decimal:
        """Calcule le montant échangé en fonction du taux de change."""
        return amount * self.rate