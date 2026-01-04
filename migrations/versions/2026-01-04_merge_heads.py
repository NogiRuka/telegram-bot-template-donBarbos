"""merge heads

Revision ID: 19a4c6386d0d
Revises: 60cd7c9b1515, 1f2a3b4c5d6e
Create Date: 2026-01-04 19:43:48.115543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19a4c6386d0d'
down_revision: Union[str, None] = ('60cd7c9b1515', '1f2a3b4c5d6e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
