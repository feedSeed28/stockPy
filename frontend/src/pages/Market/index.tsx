/** Today's market overview — 交易时段直连东方财富，盘后走本地DB */

import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Alert, Card, Col, Row, Statistic } from "antd";
import { useNavigate } from "@umijs/max";
import { useState } from "react";
import type { ProColumns } from "@ant-design/pro-components";
import axios from "axios";

import { useDirectSource } from "@/utils/dataSource";
import { fetchRealtimeMarket, type MarketItem } from "@/services/eastmoney";

const columns: ProColumns[] = [
  { title: "代码", dataIndex: "code", key: "code", width: 100, copyable: true },
  { title: "名称", dataIndex: "name", key: "name", width: 120 },
  { title: "行业", dataIndex: "industry", key: "industry", width: 100, ellipsis: true, search: false },
  {
    title: "涨跌幅",
    dataIndex: "change_pct",
    key: "change_pct",
    width: 100,
    sorter: true,
    render: (_: any, r: any) => (
      <span style={{ color: (r.change_pct || 0) >= 0 ? "#cf1322" : "#3f8600", fontWeight: "bold" }}>
        {(r.change_pct || 0) > 0 ? "+" : ""}{r.change_pct?.toFixed(2)}%
      </span>
    ),
  },
  { title: "涨跌额", dataIndex: "change_amount", key: "change_amount", width: 80, search: false,
    render: (_: any, r: any) => (
      <span style={{ color: (r.change_amount || 0) >= 0 ? "#cf1322" : "#3f8600" }}>{r.change_amount?.toFixed(2)}</span>
    )},
  { title: "收盘", dataIndex: "close", key: "close", width: 80, search: false },
  { title: "开盘", dataIndex: "open", key: "open", width: 80, search: false },
  { title: "最高", dataIndex: "high", key: "high", width: 80, search: false },
  { title: "最低", dataIndex: "low", key: "low", width: 80, search: false },
  { title: "成交量(手)", dataIndex: "volume", key: "volume", width: 100, search: false,
    render: (v: number) => (v ? (v / 100).toFixed(0) : "-") },
  { title: "成交额(亿)", dataIndex: "amount", key: "amount", width: 100, search: false,
    render: (v: number) => (v ? (v / 1e8).toFixed(2) : "-") },
  { title: "换手率", dataIndex: "turnover_rate", key: "turnover_rate", width: 80, search: false,
    render: (v: number) => (v ? v.toFixed(2) + "%" : "-") },
  { title: "振幅", dataIndex: "amplitude", key: "amplitude", width: 80, search: false,
    render: (v: number) => (v ? v.toFixed(2) + "%" : "-") },
];

/** 将东方财富数据格式转换为页面统一格式 */
function mapEMItem(item: MarketItem): Record<string, any> {
  return {
    code: item.code,
    name: item.name,
    industry: "",
    change_pct: item.changePct,
    change_amount: item.changeAmt,
    close: item.price,
    open: item.open,
    high: item.high,
    low: item.low,
    volume: item.volume,
    amount: item.amount,
    turnover_rate: item.turnover,
    amplitude: item.amplitude,
  };
}

export default function MarketPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({ up: 0, down: 0, flat: 0, total: 0, date: "" });

  return (
    <PageContainer title={stats.date ? `行情概览 — ${stats.date}` : "行情概览"}>
      {/* 数据源提示 */}
      <Alert
        type="info"
        message="行情数据优先直连东方财富 API（用户IP），失败时自动回退本地数据库"
        style={{ marginBottom: 16 }}
        showIcon
        closable
      />

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card><Statistic title="📈 上涨" value={stats.up} valueStyle={{ color: "#cf1322" }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="📉 下跌" value={stats.down} valueStyle={{ color: "#3f8600" }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="➖ 平盘" value={stats.flat} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="📊 总数" value={stats.total} /></Card>
        </Col>
      </Row>

      <ProTable
        columns={columns}
        rowKey="code"
        request={async (params: Record<string, any>) => {
          // ── 直连模式：优先东方财富 ──
          if (useDirectSource()) {
            const page = params.current ?? 1;
            const pageSize = params.pageSize ?? 50;
            try {
              const result = await fetchRealtimeMarket(page, pageSize);
              if (result && result.items.length > 0) {
                const items = result.items.map(mapEMItem);
                const up = items.filter((i: any) => i.change_pct > 0).length;
                const down = items.filter((i: any) => i.change_pct < 0).length;
                const flat = items.filter((i: any) => i.change_pct === 0).length;
                setStats({ up, down, flat, total: result.total, date: new Date().toLocaleDateString("zh-CN") });
                return { data: items, total: result.total, success: true };
              }
            } catch {}
          }

          // ── 后端模式 / 东方财富失败 → 后端DB ──
          const sortBy = params.sorter?.field || "change_pct";
          const order = params.sorter?.order === "ascend" ? "asc" : "desc";
          try {
            const { data } = await axios.get("/api/v1/market/today", {
              params: { page: params.current, page_size: params.pageSize, sort_by: sortBy, order },
            });
            if (data.code === 200) {
              const d = data.data;
              setStats({
                up: d.stats?.up || 0, down: d.stats?.down || 0,
                flat: d.stats?.flat || 0, total: d.total || 0, date: d.date || "",
              });
              return { data: d.items, total: d.total, success: true };
            }
          } catch {}
          return { data: [], total: 0, success: true };
        }}
        search={false}
        onRow={(r) => ({ onClick: () => navigate(`/stocks/${r.code}`), style: { cursor: "pointer" } })}
        pagination={{ defaultPageSize: 50, showSizeChanger: true }}
        scroll={{ y: 500 }}
        dateFormatter="string"
      />
    </PageContainer>
  );
}
