"""add_watchlist_tables

Revision ID: 75758fa0a58a
Revises: 20260629_0001
Create Date: 2026-07-24 20:00:17.297385

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "75758fa0a58a"
down_revision: Union[str, None] = "20260629_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist_group",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="主键 UUID"),
        sa.Column("name", sa.String(length=50), nullable=False, comment="分组名称"),
        sa.Column("sort_order", sa.Integer(), nullable=False, comment="分组排序"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="更新时间",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "watchlist_item",
        sa.Column("id", sa.CHAR(length=36), nullable=False, comment="主键 UUID"),
        sa.Column("group_id", sa.CHAR(length=36), nullable=False, comment="分组 ID"),
        sa.Column("stock_code", sa.String(length=6), nullable=False, comment="股票代码"),
        sa.Column("sort_order", sa.Integer(), nullable=False, comment="组内排序"),
        sa.Column("note", sa.String(length=200), nullable=True, comment="备注"),
        sa.Column("added_at", sa.Date(), nullable=True, comment="加入日期"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="更新时间",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["watchlist_group.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "stock_code", name="uk_group_stock"),
    )


def downgrade() -> None:
    op.drop_table("watchlist_item")
    op.drop_table("watchlist_group")
