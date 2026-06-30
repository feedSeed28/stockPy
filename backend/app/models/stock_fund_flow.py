"""A-stock fund flow model."""

from datetime import date

from sqlalchemy import Date, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDMixin, TimestampMixin, Base


class StockFundFlowDaily(Base, UUIDMixin, TimestampMixin):
    """A股每日资金流向 — 主力/超大单/大单/中单/小单."""

    __tablename__ = "stock_fund_flow_daily"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uq_stock_fundflow_date"),
    )

    stock_code: Mapped[str] = mapped_column(
        String(6), nullable=False, index=True, comment="股票代码"
    )
    trade_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="交易日期"
    )
    close: Mapped[float | None] = mapped_column(Float, nullable=True, comment="收盘价")
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌幅%")
    main_net_inflow: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="主力净流入-净额"
    )
    main_net_ratio: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="主力净流入-净占比%"
    )
    huge_net_inflow: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="超大单净流入-净额"
    )
    huge_net_ratio: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="超大单净流入-净占比%"
    )
    large_net_inflow: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="大单净流入-净额"
    )
    large_net_ratio: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="大单净流入-净占比%"
    )
    medium_net_inflow: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="中单净流入-净额"
    )
    medium_net_ratio: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="中单净流入-净占比%"
    )
    small_net_inflow: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="小单净流入-净额"
    )
    small_net_ratio: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="小单净流入-净占比%"
    )
