"""Fix quiz user_id BigInteger

Revision ID: 83ea159c2541
Revises: 72db368f1634
Create Date: 2026-01-01 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '83ea159c2541'
down_revision: Union[str, None] = 'change_expire_at_datetime'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # quiz_active_sessions
    op.alter_column('quiz_active_sessions', 'user_id',
               existing_type=mysql.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               existing_comment='用户ID (单人单会话)')
    op.alter_column('quiz_active_sessions', 'chat_id',
               existing_type=mysql.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               existing_comment='聊天ID')
    op.alter_column('quiz_active_sessions', 'message_id',
               existing_type=mysql.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               existing_comment='题目消息ID')

    # quiz_logs
    op.alter_column('quiz_logs', 'user_id',
               existing_type=mysql.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               existing_comment='用户ID')
    op.alter_column('quiz_logs', 'chat_id',
               existing_type=mysql.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               existing_comment='聊天ID')


def downgrade() -> None:
    # quiz_logs
    op.alter_column('quiz_logs', 'chat_id',
               existing_type=sa.BigInteger(),
               type_=mysql.INTEGER(),
               existing_nullable=False,
               existing_comment='聊天ID')
    op.alter_column('quiz_logs', 'user_id',
               existing_type=sa.BigInteger(),
               type_=mysql.INTEGER(),
               existing_nullable=False,
               existing_comment='用户ID')

    # quiz_active_sessions
    op.alter_column('quiz_active_sessions', 'message_id',
               existing_type=sa.BigInteger(),
               type_=mysql.INTEGER(),
               existing_nullable=False,
               existing_comment='题目消息ID')
    op.alter_column('quiz_active_sessions', 'chat_id',
               existing_type=sa.BigInteger(),
               type_=mysql.INTEGER(),
               existing_nullable=False,
               existing_comment='聊天ID')
    op.alter_column('quiz_active_sessions', 'user_id',
               existing_type=sa.BigInteger(),
               type_=mysql.INTEGER(),
               existing_nullable=False,
               existing_comment='用户ID (单人单会话)')
