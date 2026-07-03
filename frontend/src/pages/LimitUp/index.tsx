/** Limit-up stocks — card layout with period selector */

import { PageContainer } from "@ant-design/pro-components";
import { Card, Col, InputNumber, Row, Tag, Typography, Spin, Empty, Button, Space } from "antd";
import { useLocation, useNavigate } from "@umijs/max";
import { useEffect, useState } from "react";
import axios from "axios";

const { Text, Title } = Typography;

const BOARD_MAP: Record<string, { title: string; param: string }> = {
  "/limit-up/main": { title: "主板", param: "主板" },
  "/limit-up/chinext": { title: "创业板", param: "创业板" },
  "/limit-up/star": { title: "科创板", param: "科创板" },
};

const PERIODS = [
  { label: "今日", days: 1 },
  { label: "五日", days: 5 },
  { label: "十日", days: 10 },
  { label: "二十日", days: 20 },
];

export default function LimitUpPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const board = BOARD_MAP[location.pathname] || BOARD_MAP["/limit-up/main"];
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(1);
  const [customDays, setCustomDays] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    const d = customDays && customDays > 0 ? customDays : days;
    axios
      .get("/api/v1/limit-up/period", { params: { days: d, board_type: board.param } })
      .then(({ data }) => {
        if (data.code === 200) setItems(data.data.items || []);
      })
      .finally(() => setLoading(false));
  }, [board.param, days, customDays]);

  if (loading) return <PageContainer title={`涨停板 — ${board.title}`}><Spin size="large" style={{display:"block",margin:"100px auto"}}/></PageContainer>;

  return (
    <PageContainer title={`涨停板 — ${board.title}（${items.length}只）`}>
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
        <Empty description={`近${customDays || days}天暂无涨停数据（可能该板块交易日数据未同步）`} />
      ) : (
        <Row gutter={[12, 12]}>
          {items.map((stock) => (
            <Col key={stock.code} xs={24} sm={12} md={8} lg={6} xl={4}>
              <Card
                hoverable
                size="small"
                onClick={() => navigate(`/stocks/${stock.code}`)}
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
