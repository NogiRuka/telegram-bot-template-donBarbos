"""merge multiple heads

Revision ID: b5d0d58ef028
Revises: e405e1effaed, a1b9c7d2e4f0, b8c7a6d5e4f1, add_emby_user_dates
Create Date: 2025-12-12 03:37:23.783095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5d0d58ef028'
down_revision: Union[str, None] = ('e405e1effaed', 'a1b9c7d2e4f0', 'b8c7a6d5e4f1', 'add_emby_user_dates')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
