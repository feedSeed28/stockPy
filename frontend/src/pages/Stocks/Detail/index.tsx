/** Stock detail page */

import { PageContainer } from "@ant-design/pro-components";
import { Card, Col, Descriptions, Row, Statistic, Tabs, message } from "antd";
import { useParams } from "@umijs/max";
import { useEffect, useState } from "react";
import { fetchStock, fetchTodaySummary } from "@/services/stock";
import type { StockInfo } from "@/services/typings";
import KlineChart from "./KlineChart";
import FinancialsView from "./FinancialsView";

export default function StockDetailPage() {
  const { code } = useParams<{ code: string }>();
  const [stock, setStock] = useState<StockInfo | null>(null);
  const [today, setToday] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
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
      )}

      {/* Limit-up stats */}
      {today && (
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
