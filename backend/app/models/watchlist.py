"""自选股——分组 + 股票二级结构.

注意：生产库 admin 用户无 REFERENCES 权限，且默认 MyISAM 引擎不支持外键约束。
因此 group_id 在数据库层只是普通列，删除分组需在应用层手动清理 items。
"""

import uuid
from datetime import date

from sqlalchemy import CHAR, Date, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WatchlistGroup(Base, TimestampMixin):
    """自选分组."""

    __tablename__ = "watchlist_group"

    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="主键 UUID",
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="分组名称（如 自选 / 短线 / 长线）",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="分组排序",
    )

    items: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WatchlistItem.sort_order",
    )


class WatchlistItem(Base, TimestampMixin):
    """自选股票."""

    __tablename__ = "watchlist_item"
    __table_args__ = (
        UniqueConstraint("group_id", "stock_code", name="uk_group_stock"),
    )

    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="主键 UUID",
    )
    group_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("watchlist_group.id"),
        nullable=False,
        comment="分组 ID",
    )
    stock_code: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="股票代码",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="组内排序",
    )
    note: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="备注（买入理由 / 止损位等）",
    )
    added_at: Mapped[date] = mapped_column(
        Date,
        default=func.current_date(),
        comment="加入日期",
    )

    group: Mapped["WatchlistGroup"] = relationship(back_populates="items")
