/** Stock detail page — 交易时段直连东方财富，盘后走后端DB */

import { PageContainer } from "@ant-design/pro-components";
import { Card, Col, Descriptions, Row, Statistic, Tag, Tabs, message } from "antd";
import { useEffect, useState } from "react";
import { fetchStock, fetchTodaySummary } from "@/services/stock";
import type { StockInfo } from "@/services/typings";
import { useDirectSource } from "@/utils/dataSource";
import { fetchRealtimeQuote } from "@/services/eastmoney";
import KlineChart from "./KlineChart";
import FinancialsView from "./FinancialsView";

/** 从股票代码推导交易所和板块 */
function deriveInfo(code: string) {
  return {
    exchange: code.startsWith("6") ? "SH" : "SZ",
    board_type: code.startsWith("688")
      ? "科创板"
      : code.startsWith("300") || code.startsWith("301")
        ? "创业板"
        : "主板",
  };
}

export default function StockDetailPage() {
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const code = pathParts[pathParts.length - 1];
  const [stock, setStock] = useState<StockInfo | null>(null);
  const [today, setToday] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!code) return;
    setLoading(true);

    // ── 直连模式：优先东方财富，失败再走后端 ──
    if (useDirectSource()) {
      const emPromise = fetchRealtimeQuote(code)
        .then((em) => {
          if (!em) return null;
          const derived = deriveInfo(code);
          return {
            stock: {
              code: em.code, name: em.name,
              exchange: derived.exchange, board_type: derived.board_type,
              industry: "", is_active: true, listed_date: null,
              source: "live",
            } as StockInfo,
            today: {
              code: em.code,
              trade_date: new Date().toISOString().slice(0, 10),
              open: em.open, close: em.price,
              high: em.high, low: em.low,
              volume: em.volume, amount: em.amount,
              change_pct: em.changePct, change_amount: em.changeAmt,
              turnover_rate: em.turnover, amplitude: em.amplitude,
              source: "live",
            },
          };
        })
        .catch(() => null);

      const dbPromise = Promise.all([
        fetchStock(code).catch(() => null),
        fetchTodaySummary(code).catch(() => null),
      ]);

      Promise.all([emPromise, dbPromise])
        .then(([em, [dbStock, dbToday]]) => {
          if (em) {
            setStock(
              dbStock
                ? { ...em.stock, industry: dbStock.industry, listed_date: dbStock.listed_date }
                : em.stock
            );
            setToday({ ...em.today, lu_5d: dbToday?.lu_5d ?? 0, lu_30d: dbToday?.lu_30d ?? 0, lu_year: dbToday?.lu_year ?? 0 });
          } else {
            setStock(dbStock);
            setToday(dbToday);
          }
        })
        .catch(() => message.error("加载失败"))
        .finally(() => setLoading(false));
      return;
    }

    // ── 后端模式：完全走后端 ──
    Promise.all([fetchStock(code), fetchTodaySummary(code)])
      .then(([s, t]) => { setStock(s); setToday(t); })
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  }, [code]);

  if (!code) return null;

  return (
    <PageContainer title={`${stock?.name || code} (${code})`} loading={loading}>
      {/* Today's performance card */}
      {today && (
        <>
        {today.source === "live" && (
          <Tag color="red" style={{ marginBottom: 8 }}>🔥 实时数据</Tag>
        )}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Card size="small">
              <Statistic title="最新价" value={today.close?.toFixed(2)} precision={2}
                valueStyle={{ color: (today.change_pct || 0) >= 0 ? "#cf1322" : "#3f8600", fontSize: 24 }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="涨跌幅" value={today.change_pct?.toFixed(2)} suffix="%"
                valueStyle={{ color: (today.change_pct || 0) >= 0 ? "#cf1322" : "#3f8600", fontSize: 24 }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="涨跌额" value={today.change_amount?.toFixed(2)}
                valueStyle={{ color: (today.change_amount || 0) >= 0 ? "#cf1322" : "#3f8600", fontSize: 24 }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="成交额(亿)" value={(today.amount / 1e8).toFixed(2)} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="换手率" value={today.turnover_rate?.toFixed(2)} suffix="%" />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="振幅" value={today.amplitude?.toFixed(2)} suffix="%" />
            </Card>
          </Col>
        </Row>
        </>
      )}

      {/* Limit-up stats */}
      {today && (
        <>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small" style={{ background: "#fff7e6" }}>
              <Statistic title="近5日涨停" value={today.lu_5d || 0}
                valueStyle={{ color: today.lu_5d > 0 ? "#cf1322" : "#999", fontSize: 20 }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: "#fff1f0" }}>
              <Statistic title="近30日涨停" value={today.lu_30d || 0}
                valueStyle={{ color: today.lu_30d > 0 ? "#cf1322" : "#999", fontSize: 20 }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ background: "#f6ffed" }}>
              <Statistic title="今年涨停" value={today.lu_year || 0}
                valueStyle={{ color: today.lu_year > 0 ? "#cf1322" : "#999", fontSize: 20 }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="日期" value={today.trade_date || "-"} />
            </Card>
          </Col>
        </Row>
        </>
      )}

      {/* Basic info */}
      {stock && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions column={5} size="small">
            <Descriptions.Item label="代码">{stock.code}</Descriptions.Item>
            <Descriptions.Item label="名称">{stock.name}</Descriptions.Item>
            <Descriptions.Item label="交易所">{stock.exchange}</Descriptions.Item>
            <Descriptions.Item label="板块">{stock.board_type || "-"}</Descriptions.Item>
            <Descriptions.Item label="行业">{stock.industry || "-"}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* K-line + Financials */}
      <Card>
        <Tabs defaultActiveKey="kline" items={[
          { key: "kline", label: "K线图", children: <KlineChart code={code} /> },
          { key: "financials", label: "财务数据", children: <FinancialsView code={code} /> },
        ]} />
      </Card>
    </PageContainer>
  );
}
