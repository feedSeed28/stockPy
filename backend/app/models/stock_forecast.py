"""A-stock profit forecast model."""

from datetime import date

from sqlalchemy import Date, Float, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDMixin, TimestampMixin, Base


class StockProfitForecast(Base, UUIDMixin, TimestampMixin):
    """A股盈利预测 — 东方财富分析师一致预期."""

    __tablename__ = "stock_profit_forecast"
    __table_args__ = (
        UniqueConstraint("stock_code", "updated_date", name="uq_stock_forecast"),
    )

    stock_code: Mapped[str] = mapped_column(
        String(6), nullable=False, index=True, comment="股票代码"
    )
    stock_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="股票简称"
    )
    research_report_num: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="研报数"
    )
    rating_buy: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="买入评级数"
    )
    rating_overweight: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="增持评级数"
    )
    rating_neutral: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="中性评级数"
    )
    rating_underweight: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="减持评级数"
    )
    rating_sell: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="卖出评级数"
    )
    forecast_eps_year1: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="预测每股收益(第一年)"
    )
    forecast_eps_year2: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="预测每股收益(第二年)"
    )
    forecast_eps_year3: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="预测每股收益(第三年)"
    )
    forecast_eps_year4: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="预测每股收益(第四年)"
    )
    forecast_np_year1: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="预测净利润(第一年)"
    )
    forecast_np_year2: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="预测净利润(第二年)"
    )
    forecast_np_year3: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="预测净利润(第三年)"
    )
    forecast_np_year4: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="预测净利润(第四年)"
    )
    target_avg_price: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="目标均价"
    )
    updated_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="数据更新日期"
    )
