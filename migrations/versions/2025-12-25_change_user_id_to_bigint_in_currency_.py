"""change user_id to bigint in currency_transactions

Revision ID: daf005fc71d6
Revises: 81682f5d33de
Create Date: 2025-12-25 23:45:20.670310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'daf005fc71d6'
down_revision: Union[str, None] = '81682f5d33de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change user_id column type to BigInteger
    op.alter_column('currency_transactions', 'user_id',
               existing_type=sa.Integer(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               existing_comment="关联 users.id")


def downgrade() -> None:
    # Revert user_id column type to Integer
    op.alter_column('currency_transactions', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.Integer(),
               existing_nullable=False,
               existing_comment="关联 users.id")
