"""add new table with import

Revision ID: fe1fb38fc472
Revises: 52e6bd582353
Create Date: 2026-02-28 10:48:16.538036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fe1fb38fc472'
down_revision: Union[str, Sequence[str], None] = '52e6bd582353'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ledger tables: agent_wallets, ledger_transactions, ledger_entries, settlements."""

    # ══════════════════════════════════════════════════════════════
    # 1. ENUMS PostgreSQL
    # ══════════════════════════════════════════════════════════════

    # ledger_entry_type = postgresql.ENUM(
    #     'DEBIT', 'CREDIT',
    #     name='ledger_entry_type',
    #     create_type=False,
    # )
    # op.execute("CREATE TYPE ledger_entry_type AS ENUM ('DEBIT', 'CREDIT')")

    # ledger_category = postgresql.ENUM(
    #     'TRANSACTION_IN', 'TRANSACTION_OUT', 'FEE_COLLECTED',
    #     'SETTLEMENT', 'MANUAL_ADJUSTMENT', 'TOP_UP',
    #     'WITHDRAWAL', 'CORRECTION',
    #     name='ledger_category',
    #     create_type=False,
    # )
    # op.execute(
    #     "CREATE TYPE ledger_category AS ENUM ("
    #     "'TRANSACTION_IN', 'TRANSACTION_OUT', 'FEE_COLLECTED', "
    #     "'SETTLEMENT', 'MANUAL_ADJUSTMENT', 'TOP_UP', "
    #     "'WITHDRAWAL', 'CORRECTION')"
    # )

    # settlement_status = postgresql.ENUM(
    #     'PENDING', 'APPROVED', 'EXECUTED', 'CANCELLED',
    #     name='settlement_status',
    #     create_type=False,
    # )
    # op.execute(
    #     "CREATE TYPE settlement_status AS ENUM ("
    #     "'PENDING', 'APPROVED', 'EXECUTED', 'CANCELLED')"
    # )

    # ══════════════════════════════════════════════════════════════
    # 2. TABLE: agent_wallets
    # ══════════════════════════════════════════════════════════════

    op.create_table(
        'agent_wallets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('currency_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('currencies.id'), nullable=False, index=True),
        sa.Column('currency_code', sa.String(3), nullable=False),
        sa.Column('payment_method_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('payment_type.id'), nullable=True, index=True),
        sa.Column('payment_method_name', sa.String(100), nullable=True),
        sa.Column('balance', sa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sa.Column('min_balance', sa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Index unique: 1 wallet par agent/devise/méthode
    op.create_index(
        'uq_agent_currency_method',
        'agent_wallets',
        ['agent_id', 'currency_id', 'payment_method_id'],
        unique=True,
    )

    # ══════════════════════════════════════════════════════════════
    # 3. TABLE: ledger_transactions
    # ══════════════════════════════════════════════════════════════

    op.create_table(
        'ledger_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reference', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('transactions.id'), nullable=True, index=True),
        sa.Column('category', sa.Enum(
            'TRANSACTION_IN', 'TRANSACTION_OUT', 'FEE_COLLECTED',
            'SETTLEMENT', 'MANUAL_ADJUSTMENT', 'TOP_UP',
            'WITHDRAWAL', 'CORRECTION',
            name='ledger_category', create_type=False,
        ), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=True),
        sa.Column('initiated_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ══════════════════════════════════════════════════════════════
    # 4. TABLE: ledger_entries
    # ══════════════════════════════════════════════════════════════

    op.create_table(
        'ledger_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ledger_tx_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ledger_transactions.id'), nullable=False, index=True),
        sa.Column('wallet_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agent_wallets.id'), nullable=False, index=True),
        sa.Column('entry_type', sa.Enum(
            'DEBIT', 'CREDIT',
            name='ledger_entry_type', create_type=False,
        ), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency_code', sa.String(3), nullable=False),
        sa.Column('balance_after', sa.Numeric(18, 2), nullable=False),
        sa.Column('note', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Constraints
        sa.CheckConstraint('amount > 0', name='ck_ledger_amount_positive'),
    )

    # Index composites pour les requêtes fréquentes
    op.create_index('ix_ledger_wallet_created', 'ledger_entries', ['wallet_id', 'created_at'])
    op.create_index('ix_ledger_tx_type', 'ledger_entries', ['ledger_tx_id', 'entry_type'])

    # ══════════════════════════════════════════════════════════════
    # 5. TABLE: settlements
    # ══════════════════════════════════════════════════════════════

    op.create_table(
        'settlements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reference', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('from_agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('from_wallet_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agent_wallets.id'), nullable=False),
        sa.Column('to_agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('to_wallet_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agent_wallets.id'), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency_code', sa.String(3), nullable=False),
        sa.Column('target_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('target_currency_code', sa.String(3), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=True),
        sa.Column('status', sa.Enum(
            'PENDING', 'APPROVED', 'EXECUTED', 'CANCELLED',
            name='settlement_status', create_type=False,
        ), nullable=False, server_default='PENDING'),
        sa.Column('ledger_tx_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ledger_transactions.id'), nullable=True),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ══════════════════════════════════════════════════════════════
    # 6. TRIGGER: auto-update updated_at
    # ══════════════════════════════════════════════════════════════

    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_agent_wallets_updated_at
            BEFORE UPDATE ON agent_wallets
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER trigger_settlements_updated_at
            BEFORE UPDATE ON settlements
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop ledger tables and enums."""

    # Triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_settlements_updated_at ON settlements")
    op.execute("DROP TRIGGER IF EXISTS trigger_agent_wallets_updated_at ON agent_wallets")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Tables (ordre inverse des dépendances FK)
    op.drop_table('settlements')
    op.drop_table('ledger_entries')
    op.drop_table('ledger_transactions')
    op.drop_table('agent_wallets')

    # Enums
    op.execute("DROP TYPE IF EXISTS settlement_status")
    op.execute("DROP TYPE IF EXISTS ledger_category")
    op.execute("DROP TYPE IF EXISTS ledger_entry_type")