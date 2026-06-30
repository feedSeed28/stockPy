"""P1: Create all A-stock data tables.

Revision ID: 20260629_0001
Revises: 8d5b4dba6083
Create Date: 2026-06-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260629_0001"
down_revision: Union[str, None] = "8d5b4dba6083"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stock_info ──────────────────────────────────────────────
    op.create_table(
        "stock_info",
        sa.Column("code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("name", sa.String(20), nullable=False, comment="股票简称"),
        sa.Column(
            "exchange",
            sa.Enum("SH", "SZ", "BJ", name="exchange_enum"),
            nullable=False,
            comment="交易所",
        ),
        sa.Column(
            "board_type",
            sa.Enum("主板", "科创板", "创业板", "北交所", name="board_type_enum"),
            nullable=True,
            comment="板块类型",
        ),
        sa.Column("industry", sa.String(50), nullable=True, comment="所属行业"),
        sa.Column("is_active", sa.Boolean(), default=True, comment="是否上市"),
        sa.Column("listed_date", sa.Date(), nullable=True, comment="上市日期"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("code"),
    )

    # ── stock_daily_quote ───────────────────────────────────────
    op.create_table(
        "stock_daily_quote",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("stock_code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column(
            "adjust_type",
            sa.Enum("none", "qfq", "hfq", name="adjust_type_enum"),
            nullable=False,
            server_default="qfq",
            comment="复权类型",
        ),
        sa.Column("open", sa.Float(), nullable=False, comment="开盘价"),
        sa.Column("close", sa.Float(), nullable=False, comment="收盘价"),
        sa.Column("high", sa.Float(), nullable=False, comment="最高价"),
        sa.Column("low", sa.Float(), nullable=False, comment="最低价"),
        sa.Column("volume", sa.BigInteger(), nullable=False, comment="成交量(股)"),
        sa.Column("amount", sa.Float(), nullable=False, comment="成交额(元)"),
        sa.Column("amplitude", sa.Float(), nullable=True, comment="振幅%"),
        sa.Column("change_pct", sa.Float(), nullable=True, comment="涨跌幅%"),
        sa.Column("change_amount", sa.Float(), nullable=True, comment="涨跌额"),
        sa.Column("turnover_rate", sa.Float(), nullable=True, comment="换手率%"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", "trade_date", "adjust_type", name="uq_stock_date_adj"),
    )
    op.create_index("idx_daily_stock_code", "stock_daily_quote", ["stock_code"])
    op.create_index("idx_daily_trade_date", "stock_daily_quote", ["trade_date"])

    # ── stock_weekly_quote ──────────────────────────────────────
    op.create_table(
        "stock_weekly_quote",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("stock_code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column(
            "adjust_type",
            sa.Enum("none", "qfq", "hfq", name="adjust_type_enum"),
            nullable=False,
            server_default="qfq",
            comment="复权类型",
        ),
        sa.Column("open", sa.Float(), nullable=False, comment="开盘价"),
        sa.Column("close", sa.Float(), nullable=False, comment="收盘价"),
        sa.Column("high", sa.Float(), nullable=False, comment="最高价"),
        sa.Column("low", sa.Float(), nullable=False, comment="最低价"),
        sa.Column("volume", sa.BigInteger(), nullable=False, comment="成交量(股)"),
        sa.Column("amount", sa.Float(), nullable=False, comment="成交额(元)"),
        sa.Column("amplitude", sa.Float(), nullable=True, comment="振幅%"),
        sa.Column("change_pct", sa.Float(), nullable=True, comment="涨跌幅%"),
        sa.Column("change_amount", sa.Float(), nullable=True, comment="涨跌额"),
        sa.Column("turnover_rate", sa.Float(), nullable=True, comment="换手率%"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", "trade_date", "adjust_type", name="uq_stock_week_date_adj"),
    )
    op.create_index("idx_weekly_stock_code", "stock_weekly_quote", ["stock_code"])
    op.create_index("idx_weekly_trade_date", "stock_weekly_quote", ["trade_date"])

    # ── stock_monthly_quote ─────────────────────────────────────
    op.create_table(
        "stock_monthly_quote",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("stock_code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column(
            "adjust_type",
            sa.Enum("none", "qfq", "hfq", name="adjust_type_enum"),
            nullable=False,
            server_default="qfq",
            comment="复权类型",
        ),
        sa.Column("open", sa.Float(), nullable=False, comment="开盘价"),
        sa.Column("close", sa.Float(), nullable=False, comment="收盘价"),
        sa.Column("high", sa.Float(), nullable=False, comment="最高价"),
        sa.Column("low", sa.Float(), nullable=False, comment="最低价"),
        sa.Column("volume", sa.BigInteger(), nullable=False, comment="成交量(股)"),
        sa.Column("amount", sa.Float(), nullable=False, comment="成交额(元)"),
        sa.Column("amplitude", sa.Float(), nullable=True, comment="振幅%"),
        sa.Column("change_pct", sa.Float(), nullable=True, comment="涨跌幅%"),
        sa.Column("change_amount", sa.Float(), nullable=True, comment="涨跌额"),
        sa.Column("turnover_rate", sa.Float(), nullable=True, comment="换手率%"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", "trade_date", "adjust_type", name="uq_stock_month_date_adj"),
    )
    op.create_index("idx_monthly_stock_code", "stock_monthly_quote", ["stock_code"])
    op.create_index("idx_monthly_trade_date", "stock_monthly_quote", ["trade_date"])

    # ── stock_performance_report ────────────────────────────────
    op.create_table(
        "stock_performance_report",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("stock_code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("stock_name", sa.String(50), nullable=True, comment="股票简称"),
        sa.Column("report_date", sa.Date(), nullable=False, comment="报告期"),
        sa.Column("eps", sa.Float(), nullable=True, comment="每股收益"),
        sa.Column("revenue", sa.Float(), nullable=True, comment="营业总收入"),
        sa.Column("revenue_yoy", sa.Float(), nullable=True, comment="营业总收入同比增长%"),
        sa.Column("revenue_qoq", sa.Float(), nullable=True, comment="营业总收入环比增长%"),
        sa.Column("net_profit", sa.Float(), nullable=True, comment="净利润"),
        sa.Column("net_profit_yoy", sa.Float(), nullable=True, comment="净利润同比增长%"),
        sa.Column("net_profit_qoq", sa.Float(), nullable=True, comment="净利润环比增长%"),
        sa.Column("bvps", sa.Float(), nullable=True, comment="每股净资产"),
        sa.Column("roe", sa.Float(), nullable=True, comment="净资产收益率%"),
        sa.Column("cfps", sa.Float(), nullable=True, comment="每股经营现金流量"),
        sa.Column("gross_margin", sa.Float(), nullable=True, comment="销售毛利率%"),
        sa.Column("industry", sa.String(50), nullable=True, comment="所处行业"),
        sa.Column("announce_date", sa.Date(), nullable=True, comment="最新公告日期"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", "report_date", name="uq_stock_report"),
    )
    op.create_index("idx_perf_stock_code", "stock_performance_report", ["stock_code"])
    op.create_index("idx_perf_report_date", "stock_performance_report", ["report_date"])

    # ── stock_financial_indicator ───────────────────────────────
    op.create_table(
        "stock_financial_indicator",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("stock_code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("report_date", sa.Date(), nullable=False, comment="报告期"),
        # 每股指标
        sa.Column("eps_basic", sa.Float(), nullable=True, comment="基本每股收益"),
        sa.Column("eps_diluted", sa.Float(), nullable=True, comment="稀释每股收益"),
        sa.Column("bvps", sa.Float(), nullable=True, comment="每股净资产"),
        sa.Column("cfps", sa.Float(), nullable=True, comment="每股经营现金流"),
        # 盈利能力
        sa.Column("roe", sa.Float(), nullable=True, comment="净资产收益率%"),
        sa.Column("roa", sa.Float(), nullable=True, comment="总资产报酬率%"),
        sa.Column("gross_margin", sa.Float(), nullable=True, comment="销售毛利率%"),
        sa.Column("net_margin", sa.Float(), nullable=True, comment="销售净利率%"),
        # 成长能力
        sa.Column("revenue_growth", sa.Float(), nullable=True, comment="主营收入增长率%"),
        sa.Column("profit_growth", sa.Float(), nullable=True, comment="净利润增长率%"),
        sa.Column("asset_growth", sa.Float(), nullable=True, comment="总资产增长率%"),
        # 营运能力
        sa.Column("receivables_turnover", sa.Float(), nullable=True, comment="应收账款周转率"),
        sa.Column("inventory_turnover", sa.Float(), nullable=True, comment="存货周转率"),
        sa.Column("asset_turnover", sa.Float(), nullable=True, comment="总资产周转率"),
        # 偿债能力
        sa.Column("current_ratio", sa.Float(), nullable=True, comment="流动比率"),
        sa.Column("quick_ratio", sa.Float(), nullable=True, comment="速动比率"),
        sa.Column("debt_ratio", sa.Float(), nullable=True, comment="资产负债率%"),
        # 现金流量
        sa.Column("operating_cf", sa.Float(), nullable=True, comment="经营活动现金流净额"),
        sa.Column("investing_cf", sa.Float(), nullable=True, comment="投资活动现金流净额"),
        sa.Column("financing_cf", sa.Float(), nullable=True, comment="筹资活动现金流净额"),
        sa.Column("raw_data", sa.Text(), nullable=True, comment="原始指标行JSON"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", "report_date", name="uq_stock_fin_indicator"),
    )
    op.create_index("idx_fin_stock_code", "stock_financial_indicator", ["stock_code"])
    op.create_index("idx_fin_report_date", "stock_financial_indicator", ["report_date"])

    # ── stock_profit_forecast ───────────────────────────────────
    op.create_table(
        "stock_profit_forecast",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("stock_code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("stock_name", sa.String(50), nullable=True, comment="股票简称"),
        sa.Column("research_report_num", sa.Integer(), nullable=True, comment="研报数"),
        sa.Column("rating_buy", sa.SmallInteger(), nullable=True, comment="买入评级数"),
        sa.Column("rating_overweight", sa.SmallInteger(), nullable=True, comment="增持评级数"),
        sa.Column("rating_neutral", sa.SmallInteger(), nullable=True, comment="中性评级数"),
        sa.Column("rating_underweight", sa.SmallInteger(), nullable=True, comment="减持评级数"),
        sa.Column("rating_sell", sa.SmallInteger(), nullable=True, comment="卖出评级数"),
        sa.Column("forecast_eps_year1", sa.Float(), nullable=True, comment="预测每股收益(第一年)"),
        sa.Column("forecast_eps_year2", sa.Float(), nullable=True, comment="预测每股收益(第二年)"),
        sa.Column("forecast_eps_year3", sa.Float(), nullable=True, comment="预测每股收益(第三年)"),
        sa.Column("forecast_eps_year4", sa.Float(), nullable=True, comment="预测每股收益(第四年)"),
        sa.Column("forecast_np_year1", sa.Float(), nullable=True, comment="预测净利润(第一年)"),
        sa.Column("forecast_np_year2", sa.Float(), nullable=True, comment="预测净利润(第二年)"),
        sa.Column("forecast_np_year3", sa.Float(), nullable=True, comment="预测净利润(第三年)"),
        sa.Column("forecast_np_year4", sa.Float(), nullable=True, comment="预测净利润(第四年)"),
        sa.Column("target_avg_price", sa.Float(), nullable=True, comment="目标均价"),
        sa.Column("updated_date", sa.Date(), nullable=False, comment="数据更新日期"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", "updated_date", name="uq_stock_forecast"),
    )
    op.create_index("idx_forecast_stock_code", "stock_profit_forecast", ["stock_code"])

    # ── stock_fund_flow_daily ───────────────────────────────────
    op.create_table(
        "stock_fund_flow_daily",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("stock_code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("close", sa.Float(), nullable=True, comment="收盘价"),
        sa.Column("change_pct", sa.Float(), nullable=True, comment="涨跌幅%"),
        sa.Column("main_net_inflow", sa.Float(), nullable=True, comment="主力净流入-净额"),
        sa.Column("main_net_ratio", sa.Float(), nullable=True, comment="主力净流入-净占比%"),
        sa.Column("huge_net_inflow", sa.Float(), nullable=True, comment="超大单净流入-净额"),
        sa.Column("huge_net_ratio", sa.Float(), nullable=True, comment="超大单净流入-净占比%"),
        sa.Column("large_net_inflow", sa.Float(), nullable=True, comment="大单净流入-净额"),
        sa.Column("large_net_ratio", sa.Float(), nullable=True, comment="大单净流入-净占比%"),
        sa.Column("medium_net_inflow", sa.Float(), nullable=True, comment="中单净流入-净额"),
        sa.Column("medium_net_ratio", sa.Float(), nullable=True, comment="中单净流入-净占比%"),
        sa.Column("small_net_inflow", sa.Float(), nullable=True, comment="小单净流入-净额"),
        sa.Column("small_net_ratio", sa.Float(), nullable=True, comment="小单净流入-净占比%"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", "trade_date", name="uq_stock_fundflow_date"),
    )
    op.create_index("idx_fundflow_stock_code", "stock_fund_flow_daily", ["stock_code"])
    op.create_index("idx_fundflow_trade_date", "stock_fund_flow_daily", ["trade_date"])

    # ── stock_board_info ────────────────────────────────────────
    op.create_table(
        "stock_board_info",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("board_code", sa.String(20), nullable=False, comment="板块代码"),
        sa.Column("board_name", sa.String(50), nullable=False, comment="板块名称"),
        sa.Column(
            "board_type",
            sa.Enum("industry", "concept", name="board_type_enum"),
            nullable=False,
            comment="板块类型",
        ),
        sa.Column(
            "source",
            sa.Enum("em", "ths", name="board_source_enum"),
            nullable=False,
            comment="数据源",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("board_name", "board_type", "source", name="uq_board"),
    )

    # ── stock_board_member ──────────────────────────────────────
    op.create_table(
        "stock_board_member",
        sa.Column("id", sa.CHAR(36), nullable=False, comment="主键 UUID"),
        sa.Column("board_id", sa.String(36), nullable=False, comment="板块ID"),
        sa.Column("stock_code", sa.String(6), nullable=False, comment="股票代码"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("board_id", "stock_code", name="uq_board_stock"),
    )
    op.create_index("idx_board_member_board", "stock_board_member", ["board_id"])
    op.create_index("idx_board_member_stock", "stock_board_member", ["stock_code"])

    # ── sync_status ─────────────────────────────────────────────
    op.create_table(
        "sync_status",
        sa.Column("table_name", sa.String(50), nullable=False, comment="表名"),
        sa.Column("last_sync_time", sa.DateTime(), nullable=True, comment="最近同步完成时间"),
        sa.Column("last_data_date", sa.Date(), nullable=True, comment="最新数据日期"),
        sa.Column("row_count", sa.Integer(), nullable=True, comment="当前同步行数"),
        sa.Column(
            "status",
            sa.Enum("idle", "syncing", "error", name="sync_status_enum"),
            default="idle",
            comment="同步状态",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), comment="状态更新时间"),
        sa.PrimaryKeyConstraint("table_name"),
    )


def downgrade() -> None:
    op.drop_table("sync_status")
    op.drop_table("stock_board_member")
    op.drop_table("stock_board_info")
    op.drop_table("stock_fund_flow_daily")
    op.drop_table("stock_profit_forecast")
    op.drop_table("stock_financial_indicator")
    op.drop_table("stock_performance_report")
    op.drop_table("stock_monthly_quote")
    op.drop_table("stock_weekly_quote")
    op.drop_table("stock_daily_quote")
    op.drop_table("stock_info")
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS sync_status_enum")
    op.execute("DROP TYPE IF EXISTS board_source_enum")
    op.execute("DROP TYPE IF EXISTS board_type_enum")
    op.execute("DROP TYPE IF EXISTS adjust_type_enum")
    op.execute("DROP TYPE IF EXISTS board_type_enum")
    op.execute("DROP TYPE IF EXISTS exchange_enum")
