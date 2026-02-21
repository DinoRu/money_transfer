"""create_transaction_status_enum

Revision ID: 16b09e90aed5
Revises: 3b840cbb105f
Create Date: 2026-02-21 16:40:12.237379

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '16b09e90aed5'
down_revision: Union[str, Sequence[str], None] = '3b840cbb105f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Définition ENUM
transaction_status_enum = postgresql.ENUM(
    'PENDING',
    'FUNDS_DEPOSITED',
    'IN_PROGRESS',
    'COMPLETED',
    'EXPIRED',
    'CANCELLED',
    name='transaction_status'
)



def upgrade():
    # 1️⃣ Créer le type ENUM
    transaction_status_enum.create(op.get_bind())

    # 2️⃣ Modifier la colonne
    op.alter_column(
        'transactions',
        'status',
        type_=transaction_status_enum,
        existing_type=sa.String(),
        postgresql_using="status::transaction_status"
    )

def downgrade():
    op.alter_column(
        'transactions',
        'status',
        type_=sa.String(),
        existing_type=transaction_status_enum
    )

    transaction_status_enum.drop(op.get_bind())