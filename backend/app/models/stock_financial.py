"""A-stock financial data models — performance reports & financial indicators."""

from datetime import date

from sqlalchemy import Date, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDMixin, TimestampMixin, Base


class StockPerformanceReport(Base, UUIDMixin, TimestampMixin):
    """A股业绩报表 — 东方财富数据中心季度数据."""

    __tablename__ = "stock_performance_report"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uq_stock_report"),
    )

    stock_code: Mapped[str] = mapped_column(
        String(6), nullable=False, index=True, comment="股票代码"
    )
    stock_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="股票简称"
    )
    report_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="报告期 如2024-03-31"
    )
    eps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股收益")
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True, comment="营业总收入(元)")
    revenue_yoy: Mapped[float | None] = mapped_column(Float, nullable=True, comment="营业总收入同比增长%")
    revenue_qoq: Mapped[float | None] = mapped_column(Float, nullable=True, comment="营业总收入环比增长%")
    net_profit: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净利润(元)")
    net_profit_yoy: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净利润同比增长%")
    net_profit_qoq: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净利润环比增长%")
    bvps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股净资产")
    roe: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净资产收益率%")
    cfps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股经营现金流量")
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True, comment="销售毛利率%")
    industry: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="所处行业"
    )
    announce_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="最新公告日期"
    )


class StockFinancialIndicator(Base, UUIDMixin, TimestampMixin):
    """A股财务指标 — 新浪财经 / 东方财富多维度指标."""

    __tablename__ = "stock_financial_indicator"
    __table_args__ = (
        UniqueConstraint("stock_code", "report_date", name="uq_stock_fin_indicator"),
    )

    stock_code: Mapped[str] = mapped_column(
        String(6), nullable=False, index=True, comment="股票代码"
    )
    report_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="报告期"
    )
    # 每股指标
    eps_basic: Mapped[float | None] = mapped_column(Float, nullable=True, comment="基本每股收益")
    eps_diluted: Mapped[float | None] = mapped_column(Float, nullable=True, comment="稀释每股收益")
    bvps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股净资产")
    cfps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股经营现金流")
    # 盈利能力
    roe: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净资产收益率%")
    roa: Mapped[float | None] = mapped_column(Float, nullable=True, comment="总资产报酬率%")
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True, comment="销售毛利率%")
    net_margin: Mapped[float | None] = mapped_column(Float, nullable=True, comment="销售净利率%")
    # 成长能力
    revenue_growth: Mapped[float | None] = mapped_column(Float, nullable=True, comment="主营收入增长率%")
    profit_growth: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净利润增长率%")
    asset_growth: Mapped[float | None] = mapped_column(Float, nullable=True, comment="总资产增长率%")
    # 营运能力
    receivables_turnover: Mapped[float | None] = mapped_column(Float, nullable=True, comment="应收账款周转率")
    inventory_turnover: Mapped[float | None] = mapped_column(Float, nullable=True, comment="存货周转率")
    asset_turnover: Mapped[float | None] = mapped_column(Float, nullable=True, comment="总资产周转率")
    # 偿债能力
    current_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="流动比率")
    quick_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="速动比率")
    debt_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="资产负债率%")
    # 现金流量
    operating_cf: Mapped[float | None] = mapped_column(Float, nullable=True, comment="经营活动现金流净额")
    investing_cf: Mapped[float | None] = mapped_column(Float, nullable=True, comment="投资活动现金流净额")
    financing_cf: Mapped[float | None] = mapped_column(Float, nullable=True, comment="筹资活动现金流净额")
    # 原始数据 (备用整行 JSON，方便排查和扩展)
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始指标行JSON")
