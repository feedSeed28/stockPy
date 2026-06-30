"""A-stock K-line quote models (daily / weekly / monthly)."""

from datetime import date

from sqlalchemy import BigInteger, Date, Enum, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDMixin, TimestampMixin, Base


ADJUST_ENUM = Enum("none", "qfq", "hfq", name="adjust_type_enum")


class StockDailyQuote(Base, UUIDMixin, TimestampMixin):
    """A股日K线行情——数据量最大，按年份分区."""

    __tablename__ = "stock_daily_quote"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", "adjust_type", name="uq_stock_date_adj"),
    )

    stock_code: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        index=True,
        comment="股票代码",
    )
    trade_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="交易日期",
    )
    adjust_type: Mapped[str] = mapped_column(
        ADJUST_ENUM,
        nullable=False,
        default="qfq",
        comment="复权类型 none=不复权 qfq=前复权 hfq=后复权",
    )
    open: Mapped[float] = mapped_column(Float, nullable=False, comment="开盘价")
    close: Mapped[float] = mapped_column(Float, nullable=False, comment="收盘价")
    high: Mapped[float] = mapped_column(Float, nullable=False, comment="最高价")
    low: Mapped[float] = mapped_column(Float, nullable=False, comment="最低价")
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="成交量(股)")
    amount: Mapped[float] = mapped_column(Float, nullable=False, comment="成交额(元)")
    amplitude: Mapped[float | None] = mapped_column(Float, nullable=True, comment="振幅%")
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌幅%")
    change_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌额")
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="换手率%")


class StockWeeklyQuote(Base, UUIDMixin, TimestampMixin):
    """A股周K线行情."""

    __tablename__ = "stock_weekly_quote"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", "adjust_type", name="uq_stock_week_date_adj"),
    )

    stock_code: Mapped[str] = mapped_column(
        String(6), nullable=False, index=True, comment="股票代码"
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="交易日期")
    adjust_type: Mapped[str] = mapped_column(ADJUST_ENUM, nullable=False, default="qfq", comment="复权类型")
    open: Mapped[float] = mapped_column(Float, nullable=False, comment="开盘价")
    close: Mapped[float] = mapped_column(Float, nullable=False, comment="收盘价")
    high: Mapped[float] = mapped_column(Float, nullable=False, comment="最高价")
    low: Mapped[float] = mapped_column(Float, nullable=False, comment="最低价")
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="成交量(股)")
    amount: Mapped[float] = mapped_column(Float, nullable=False, comment="成交额(元)")
    amplitude: Mapped[float | None] = mapped_column(Float, nullable=True, comment="振幅%")
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌幅%")
    change_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌额")
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="换手率%")


class StockMonthlyQuote(Base, UUIDMixin, TimestampMixin):
    """A股月K线行情."""

    __tablename__ = "stock_monthly_quote"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", "adjust_type", name="uq_stock_month_date_adj"),
    )

    stock_code: Mapped[str] = mapped_column(
        String(6), nullable=False, index=True, comment="股票代码"
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="交易日期")
    adjust_type: Mapped[str] = mapped_column(ADJUST_ENUM, nullable=False, default="qfq", comment="复权类型")
    open: Mapped[float] = mapped_column(Float, nullable=False, comment="开盘价")
    close: Mapped[float] = mapped_column(Float, nullable=False, comment="收盘价")
    high: Mapped[float] = mapped_column(Float, nullable=False, comment="最高价")
    low: Mapped[float] = mapped_column(Float, nullable=False, comment="最低价")
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="成交量(股)")
    amount: Mapped[float] = mapped_column(Float, nullable=False, comment="成交额(元)")
    amplitude: Mapped[float | None] = mapped_column(Float, nullable=True, comment="振幅%")
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌幅%")
    change_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌额")
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="换手率%")
