"""refactor_transaction_status_enum

Revision ID: 3b840cbb105f
Revises: 7a85e4d353fd
Create Date: 2026-02-21 16:22:05.589863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b840cbb105f'
down_revision: Union[str, Sequence[str], None] = '7a85e4d353fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("""
        UPDATE transactions
        SET status = 'COMPLETED'
        WHERE status IN ('Effectuée', 'Terminée')
    """)

    op.execute("""
        UPDATE transactions
        SET status = 'FUNDS_DEPOSITED'
        WHERE status = 'Dépôt confirmé'
    """)

    op.execute("""
        UPDATE transactions
        SET status = 'IN_PROGRESS'
        WHERE status = 'En cours'
    """)

    op.execute("""
        UPDATE transactions
        SET status = 'EXPIRED'
        WHERE status = 'Expirée'
    """)

    op.execute("""
        UPDATE transactions
        SET status = 'CANCELLED'
        WHERE status = 'Annulée'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
