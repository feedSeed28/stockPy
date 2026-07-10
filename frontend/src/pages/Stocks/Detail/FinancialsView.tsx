/** Financial indicators table and trend chart — 直连模式优先东方财富 */

import { useEffect, useState } from "react";
import { Space, Table, Tag, Spin, message } from "antd";
import ReactECharts from "echarts-for-react";
import {
  fetchFinancialIndicators,
  fetchPerformanceReports,
} from "@/services/stock";
import type { FinancialIndicator, PerformanceReport } from "@/services/typings";
import { useDirectSource } from "@/utils/dataSource";
import {
  fetchFinancialsEM,
  fetchPerformanceEM,
  type EMFinancialIndicator,
  type EMPerformanceReport,
} from "@/services/eastmoney";

interface Props {
  code: string;
}

/** EM 财务指标 → 页面统一格式 */
function mapEMFinancial(d: EMFinancialIndicator, idx: number): FinancialIndicator {
  return {
    report_date: d.reportDate,
    eps_basic: d.epsBasic,
    eps_diluted: d.epsDiluted,
    bvps: d.bvps,
    cfps: d.cfps,
    roe: d.roe,
    roa: d.roa,
    gross_margin: d.grossMargin,
    net_margin: d.netMargin,
    revenue_growth: d.revenueGrowth,
    profit_growth: d.profitGrowth,
  } as FinancialIndicator;
}

/** EM 业绩报表 → 页面统一格式 */
function mapEMPerf(d: EMPerformanceReport, idx: number): PerformanceReport {
  return {
    report_date: d.reportDate,
    eps: d.eps,
    revenue: d.revenue,
    revenue_yoy: d.revenueYoy,
    net_profit: d.netProfit,
    net_profit_yoy: d.netProfitYoy,
    bvps: d.bvps,
    roe: d.roe,
    cfps: d.cfps,
    gross_margin: d.grossMargin,
  } as PerformanceReport;
}

export default function FinancialsView({ code }: Props) {
  const [indicators, setIndicators] = useState<FinancialIndicator[]>([]);
  const [reports, setReports] = useState<PerformanceReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState<"db" | "live">("db");
  const direct = useDirectSource();

  useEffect(() => {
    if (!code) return;
    setLoading(true);

    if (direct) {
      // ── 直连模式：东方财富财务API ──
      Promise.all([
        fetchFinancialsEM(code),
        fetchPerformanceEM(code),
      ])
        .then(([emFin, emPerf]) => {
          setIndicators(emFin.map(mapEMFinancial));
          setReports(emPerf.map(mapEMPerf));
          setSource("live");
        })
        .catch(() => message.error("财务数据加载失败"))
        .finally(() => setLoading(false));
      return;
    }

    // ── 后端模式 ──
    Promise.all([
      fetchFinancialIndicators(code, 1, 20),
      fetchPerformanceReports(code, 1, 20),
    ])
      .then(([indRes, perfRes]) => {
        setIndicators(indRes.items);
        setReports(perfRes.items);
        setSource("db");
      })
      .catch(() => message.error("财务数据加载失败"))
      .finally(() => setLoading(false));
  }, [code, direct]);

  // Revenue & Profit trend
  const trendOption = {
    tooltip: { trigger: "axis" },
    legend: { data: ["营收", "净利润"], bottom: 0 },
    grid: { left: "8%", right: "4%", top: "8%", bottom: "12%" },
    xAxis: {
      type: "category",
      data: reports
        .map((r) => r.report_date)
        .reverse(),
    },
    yAxis: { type: "value" },
    series: [
      {
        name: "营收",
        type: "bar",
        data: reports
          .map((r) => (r.revenue ? (r.revenue / 1e8).toFixed(2) : null))
          .reverse(),
      },
      {
        name: "净利润",
        type: "line",
        data: reports
          .map((r) =>
            r.net_profit ? (r.net_profit / 1e8).toFixed(2) : null
          )
          .reverse(),
      },
    ],
  };

  const indColumns = [
    { title: "报告期", dataIndex: "report_date", key: "report_date", width: 120 },
    { title: "基本EPS", dataIndex: "eps_basic", key: "eps_basic", width: 90 },
    { title: "ROE(%)", dataIndex: "roe", key: "roe", width: 90 },
    { title: "毛利率(%)", dataIndex: "gross_margin", key: "gross_margin", width: 90 },
    { title: "净利率(%)", dataIndex: "net_margin", key: "net_margin", width: 90 },
    { title: "营收增长(%)", dataIndex: "revenue_growth", key: "revenue_growth", width: 100 },
    { title: "利润增长(%)", dataIndex: "profit_growth", key: "profit_growth", width: 100 },
    { title: "流动比率", dataIndex: "current_ratio", key: "current_ratio", width: 90 },
    { title: "速动比率", dataIndex: "quick_ratio", key: "quick_ratio", width: 90 },
    { title: "资产负债率(%)", dataIndex: "debt_ratio", key: "debt_ratio", width: 110 },
  ];

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ fontWeight: "bold", fontSize: 16 }}>
            营收与净利润趋势（亿元）
          </div>
          {source === "live" && <Tag color="orange">🔥 直连</Tag>}
        </div>
        <ReactECharts
          option={trendOption}
          style={{ height: 350 }}
          notMerge
          lazyUpdate
        />

        <div style={{ fontWeight: "bold", fontSize: 16 }}>
          财务指标
        </div>
        <Table
          dataSource={indicators}
          columns={indColumns}
          rowKey="report_date"
          pagination={false}
          scroll={{ x: 1000 }}
          size="small"
        />
      </Space>
    </Spin>
  );
}
