"""creer all new tables

Revision ID: 52e6bd582353
Revises: ed377b970de7
Create Date: 2026-02-28 10:18:01.815152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52e6bd582353'
down_revision: Union[str, Sequence[str], None] = 'ed377b970de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
