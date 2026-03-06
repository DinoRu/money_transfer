"""create ledger tables

Revision ID: 10654118aa65
Revises: 16b09e90aed5
Create Date: 2026-02-28 09:41:06.294340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10654118aa65'
down_revision: Union[str, Sequence[str], None] = '16b09e90aed5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
