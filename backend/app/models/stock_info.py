"""A-stock basic info model."""

from datetime import date

from sqlalchemy import Boolean, Date, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StockInfo(Base, TimestampMixin):
    """A股基本信息 —— 代码、名称、交易所、板块、行业、上市状态."""

    __tablename__ = "stock_info"

    code: Mapped[str] = mapped_column(
        String(6),
        primary_key=True,
        comment="股票代码",
    )
    name: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="股票简称",
    )
    exchange: Mapped[str] = mapped_column(
        Enum("SH", "SZ", "BJ", name="exchange_enum"),
        nullable=False,
        comment="交易所 SH=上海 SZ=深圳 BJ=北京",
    )
    board_type: Mapped[str | None] = mapped_column(
        Enum("主板", "科创板", "创业板", "北交所", name="board_type_enum"),
        nullable=True,
        comment="板块类型",
    )
    industry: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="所属行业",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否仍在上市",
    )
    listed_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="上市日期",
    )
