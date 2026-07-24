/** Limit-up stocks — card layout with period selector
 *  今日(交易时段): 前端直连东方财富 (用户IP) + 后端补充涨停统计
 *  多日/盘后: 后端DB查询
 */

import { PageContainer } from "@ant-design/pro-components";
import { Card, Col, InputNumber, Row, Tag, Typography, Spin, Empty, Button, Space, Alert } from "antd";
import { useEffect, useState } from "react";

import { getStockDataProvider } from "@/services/dataProvider";

const { Text, Title } = Typography;

const BOARD_MAP: Record<string, { title: string; codePrefixes: string[] }> = {
  "/limit-up/main": { title: "主板", codePrefixes: ["600", "601", "603", "605", "000", "001", "002", "003"] },
  "/limit-up/chinext": { title: "创业板", codePrefixes: ["300", "301"] },
  "/limit-up/star": { title: "科创板", codePrefixes: ["688"] },
};

const PERIODS = [
  { label: "今日", days: 1 },
  { label: "五日", days: 5 },
  { label: "十日", days: 10 },
  { label: "二十日", days: 20 },
];

export default function LimitUpPage() {
  const board = BOARD_MAP[window.location.pathname] || BOARD_MAP["/limit-up/main"];
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(1);
  const [customDays, setCustomDays] = useState<number | null>(null);
  const [source, setSource] = useState<"db" | "live">("db");

  const activeDays = customDays && customDays > 0 ? customDays : days;
  const provider = getStockDataProvider();

  useEffect(() => {
    setLoading(true);
    const d = customDays && customDays > 0 ? customDays : days;

    provider.getLimitUp({
      days: d,
      board_type: board.title,
      code_prefixes: board.codePrefixes,
    }).then((result) => {
      setItems(result.items);
      setSource(result.source === "direct" ? "live" : "db");
    }).catch(() => {
      setItems([]);
    }).finally(() => setLoading(false));
  }, [board.title, board.codePrefixes, days, customDays]);

  if (loading) return <PageContainer title={`涨停板 — ${board.title}`}><Spin size="large" style={{display:"block",margin:"100px auto"}}/></PageContainer>;

  return (
    <PageContainer title={`涨停板 — ${board.title}（${items.length}只）`}>
      {/* 数据源提示 */}
      <Alert
        type={source === "live" ? "warning" : "info"}
        message={source === "live"
          ? "🔥 实时数据 — 直连东方财富 (用户IP)，涨停统计来自本地数据库"
          : "💾 本地数据库 — 历史涨停记录"
        }
        style={{ marginBottom: 12 }}
        showIcon
        closable
      />

      {/* Period selector */}
      <Space style={{ marginBottom: 16 }} wrap>
        {PERIODS.map((p) => (
          <Button
            key={p.days}
            type={days === p.days && !customDays ? "primary" : "default"}
            onClick={() => { setDays(p.days); setCustomDays(null); }}
          >
            {p.label}
          </Button>
        ))}
        <InputNumber
          placeholder="自定义天数"
          min={1}
          max={365}
          value={customDays}
          onChange={(v) => { if (v) { setCustomDays(v); setDays(0); } else { setCustomDays(null); setDays(1); } }}
          style={{ width: 120 }}
          addonAfter="天"
        />
      </Space>

      {!items.length ? (
        <Empty description={`近${activeDays}天暂无涨停数据`} />
      ) : (
        <Row gutter={[12, 12]}>
          {items.map((stock) => (
            <Col key={stock.code} xs={24} sm={12} md={8} lg={6} xl={4}>
              <Card
                hoverable
                size="small"
                onClick={() => window.location.assign(`/stocks/${stock.code}`)}
                style={{ borderRadius: 8, borderTop: "3px solid #cf1322" }}
              >
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <Text strong style={{ fontSize: 14 }}>{stock.name}</Text>
                  <Text type="secondary" copyable={{ text: stock.code }} style={{ fontSize: 12 }}>
                    {stock.code}
                  </Text>
                </div>

                {/* Price + Change */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
                  <Title level={4} style={{ margin: 0, color: "#cf1322" }}>
                    {stock.price?.toFixed(2)}
                  </Title>
                  <Tag color="red" style={{ fontSize: 14, padding: "2px 8px" }}>
                    +{stock.change_pct?.toFixed(2)}%
                  </Tag>
                </div>

                {/* Stats grid */}
                <Row gutter={[4, 4]}>
                  <Col span={12}>
                    <Text type="secondary" style={{ fontSize: 11 }}>涨停次数</Text>
                    <br />
                    <Text strong style={{ color: "#cf1322", fontSize: 15 }}>
                      {stock.count || 0}次
                    </Text>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary" style={{ fontSize: 11 }}>最近日期</Text>
                    <br />
                    <Text style={{ fontSize: 12 }}>{stock.trade_date || "-"}</Text>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary" style={{ fontSize: 11 }}>换手率</Text>
                    <br />
                    <Text>{stock.turnover?.toFixed(2)}%</Text>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary" style={{ fontSize: 11 }}>成交额</Text>
                    <br />
                    <Text style={{ fontSize: 12 }}>{(stock.amount / 1e8).toFixed(1)}亿</Text>
                  </Col>
                </Row>

                {/* Historical stats */}
                <div style={{ marginTop: 8, borderTop: "1px solid #f0f0f0", paddingTop: 6 }}>
                  <Row gutter={[8, 0]}>
                    <Col span={8} style={{ textAlign: "center" }}>
                      <Text type="secondary" style={{ fontSize: 10 }}>近5日</Text>
                      <br />
                      <Text strong style={{ fontSize: 14, color: stock.stats_5d > 0 ? "#cf1322" : "#999" }}>
                        {stock.stats_5d || 0}
                      </Text>
                    </Col>
                    <Col span={8} style={{ textAlign: "center" }}>
                      <Text type="secondary" style={{ fontSize: 10 }}>近30日</Text>
                      <br />
                      <Text strong style={{ fontSize: 14, color: stock.stats_30d > 0 ? "#cf1322" : "#999" }}>
                        {stock.stats_30d || 0}
                      </Text>
                    </Col>
                    <Col span={8} style={{ textAlign: "center" }}>
                      <Text type="secondary" style={{ fontSize: 10 }}>今年</Text>
                      <br />
                      <Text strong style={{ fontSize: 14, color: stock.stats_year > 0 ? "#cf1322" : "#999" }}>
                        {stock.stats_year || 0}
                      </Text>
                    </Col>
                  </Row>
                </div>

                {/* Industry */}
                <div style={{ marginTop: 6, borderTop: "1px solid #f0f0f0", paddingTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {stock.industry || "—"}
                  </Text>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </PageContainer>
  );
}
