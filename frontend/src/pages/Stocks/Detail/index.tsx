/** Stock detail page — info card + K-line chart + financials. */

import { PageContainer } from "@ant-design/pro-components";
import { Card, Descriptions, Tabs, Tag, message } from "antd";
import { useParams } from "@umijs/max";
import { useEffect, useState } from "react";
import { fetchStock } from "@/services/stock";
import type { StockInfo } from "@/services/typings";
import KlineChart from "./KlineChart";
import FinancialsView from "./FinancialsView";

export default function StockDetailPage() {
  const { code } = useParams<{ code: string }>();
  const [stock, setStock] = useState<StockInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    fetchStock(code)
      .then(setStock)
      .catch(() => message.error("Failed to load stock info"))
      .finally(() => setLoading(false));
  }, [code]);

  if (!code) return null;

  const exchangeColor: Record<string, string> = {
    SH: "red",
    SZ: "green",
    BJ: "blue",
  };

  return (
    <PageContainer
      title={`${stock?.name || code} (${code})`}
      loading={loading}
    >
      {stock && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions column={4} size="small">
            <Descriptions.Item label="代码">{stock.code}</Descriptions.Item>
            <Descriptions.Item label="名称">{stock.name}</Descriptions.Item>
            <Descriptions.Item label="交易所">
              <span style={{ color: exchangeColor[stock.exchange] }}>
                {stock.exchange}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="板块">
              {stock.board_type || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="行业">
              {stock.industry || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {stock.is_active ? "✅ 上市" : "❌ 退市"}
            </Descriptions.Item>
            <Descriptions.Item label="上市日期">
              {stock.listed_date || "-"}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Card>
        <Tabs
          defaultActiveKey="kline"
          items={[
            {
              key: "kline",
              label: "K线图",
              children: <KlineChart code={code} />,
            },
            {
              key: "financials",
              label: "财务数据",
              children: <FinancialsView code={code} />,
            },
          ]}
        />
      </Card>
    </PageContainer>
  );
}
