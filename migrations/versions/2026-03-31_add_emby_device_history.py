"""add_emby_device_history

Revision ID: add_emby_device_history
Revises: 7e608d3a299c
Create Date: 2026-03-31 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_emby_device_history"
down_revision: Union[str, None] = "7e608d3a299c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "emby_device_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="自增整数主键"),
        sa.Column("emby_device_id", sa.String(length=64), nullable=False, comment="Emby 设备ID"),
        sa.Column("device_pk", sa.Integer(), nullable=True, comment="设备主表ID快照"),
        sa.Column("reported_device_id", sa.String(length=128), nullable=True, comment="上报设备ID快照"),
        sa.Column("last_user_id", sa.String(length=64), nullable=True, comment="最后使用用户ID快照"),
        sa.Column("action", sa.String(length=32), nullable=False, comment="动作类型(create/update/delete/restore)"),
        sa.Column("source", sa.String(length=32), nullable=False, comment="来源(sync/user/system)"),
        sa.Column("changed_fields", sa.JSON(), nullable=True, comment="变更字段列表"),
        sa.Column("before_data", sa.JSON(), nullable=True, comment="变更前快照"),
        sa.Column("after_data", sa.JSON(), nullable=True, comment="变更后快照"),
        sa.Column("diff_data", sa.JSON(), nullable=True, comment="字段级差异(old/new)"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="记录创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="记录更新时间"),
        sa.Column("created_by", sa.BigInteger(), nullable=True, comment="创建者用户ID"),
        sa.Column("updated_by", sa.BigInteger(), nullable=True, comment="最后更新者用户ID"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="软删除标记"),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="软删除时间"),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True, comment="删除者用户ID"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注（长文本）"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emby_device_history_action"), "emby_device_history", ["action"], unique=False)
    op.create_index(op.f("ix_emby_device_history_created_by"), "emby_device_history", ["created_by"], unique=False)
    op.create_index(op.f("ix_emby_device_history_deleted_by"), "emby_device_history", ["deleted_by"], unique=False)
    op.create_index(op.f("ix_emby_device_history_device_pk"), "emby_device_history", ["device_pk"], unique=False)
    op.create_index(op.f("ix_emby_device_history_emby_device_id"), "emby_device_history", ["emby_device_id"], unique=False)
    op.create_index(op.f("ix_emby_device_history_is_deleted"), "emby_device_history", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_emby_device_history_last_user_id"), "emby_device_history", ["last_user_id"], unique=False)
    op.create_index(op.f("ix_emby_device_history_reported_device_id"), "emby_device_history", ["reported_device_id"], unique=False)
    op.create_index(op.f("ix_emby_device_history_source"), "emby_device_history", ["source"], unique=False)
    op.create_index(op.f("ix_emby_device_history_updated_by"), "emby_device_history", ["updated_by"], unique=False)
    op.create_index("idx_emby_device_history_device_action", "emby_device_history", ["emby_device_id", "action"], unique=False)
    op.create_index("idx_emby_device_history_device_created", "emby_device_history", ["emby_device_id", "created_at"], unique=False)
    op.create_index("idx_emby_device_history_user_created", "emby_device_history", ["last_user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_emby_device_history_user_created", table_name="emby_device_history")
    op.drop_index("idx_emby_device_history_device_created", table_name="emby_device_history")
    op.drop_index("idx_emby_device_history_device_action", table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_updated_by"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_source"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_reported_device_id"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_last_user_id"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_is_deleted"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_emby_device_id"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_device_pk"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_deleted_by"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_created_by"), table_name="emby_device_history")
    op.drop_index(op.f("ix_emby_device_history_action"), table_name="emby_device_history")
    op.drop_table("emby_device_history")
