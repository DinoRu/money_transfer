"""change class name

Revision ID: ed377b970de7
Revises: 10654118aa65
Create Date: 2026-02-28 09:51:14.782678

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed377b970de7'
down_revision: Union[str, Sequence[str], None] = '10654118aa65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
