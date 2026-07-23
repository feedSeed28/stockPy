/** Stock screener — build filter conditions, scan all A-stocks. */

import { PageContainer } from "@ant-design/pro-components";
import {
  Button,
  Card,
  Select,
  InputNumber,
  Space,
  Table,
  Tag,
  message,
  Form,
  Popconfirm,
} from "antd";
import { useState } from "react";
import { runScreener } from "@/services/stock";

const FIELD_OPTIONS = [
  { label: "ROE (%)", value: "roe" },
  { label: "毛利率 (%)", value: "gross_margin" },
  { label: "营收增长率 (%)", value: "revenue_growth" },
  { label: "利润增长率 (%)", value: "profit_growth" },
  { label: "资产负债率 (%)", value: "debt_ratio" },
  { label: "流动比率", value: "current_ratio" },
  { label: "基本EPS", value: "eps_basic" },
  { label: "每股净资产", value: "bvps" },
  { label: "MA金叉", value: "ma_cross" },
  { label: "MACD金叉", value: "macd_cross" },
  { label: "RSI", value: "rsi" },
];

const OP_OPTIONS: Record<string, { label: string; value: string }[]> = {
  roe: [
    { label: ">", value: "gt" },
    { label: "<", value: "lt" },
  ],
  gross_margin: [
    { label: ">", value: "gt" },
    { label: "<", value: "lt" },
  ],
  revenue_growth: [
    { label: ">", value: "gt" },
    { label: "<", value: "lt" },
  ],
  profit_growth: [
    { label: ">", value: "gt" },
    { label: "<", value: "lt" },
  ],
  debt_ratio: [
    { label: ">", value: "gt" },
    { label: "<", value: "lt" },
  ],
  current_ratio: [
    { label: ">", value: "gt" },
    { label: "<", value: "lt" },
  ],
  eps_basic: [
    { label: ">", value: "gt" },
    { label: "<", value: "lt" },
  ],
  bvps: [
    { label: ">", value: "gt" },
    { label: "<", value: "lt" },
  ],
  ma_cross: [{ label: "金叉", value: "golden" }],
  macd_cross: [{ label: "金叉", value: "golden" }],
  rsi: [
    { label: "<", value: "lt" },
    { label: ">", value: "gt" },
  ],
};

interface ConditionRow {
  key: string;
  field: string;
  op: string;
  value?: number;
  params?: Record<string, any>;
}

export default function ScreenerPage() {
  const [conditions, setConditions] = useState<ConditionRow[]>([
    { key: "1", field: "roe", op: "gt", value: 15 },
  ]);
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const addCondition = () => {
    const key = String(Date.now());
    setConditions([...conditions, { key, field: "roe", op: "gt", value: 10 }]);
  };

  const removeCondition = (key: string) => {
    setConditions(conditions.filter((c) => c.key !== key));
  };

  const updateCondition = (key: string, updates: Partial<ConditionRow>) => {
    setConditions(
      conditions.map((c) => (c.key === key ? { ...c, ...updates } : c))
    );
  };

  const handleSearch = async () => {
    setLoading(true);
    try {
      const res = await runScreener({
        conditions: conditions.map((c) => ({
          field: c.field,
          op: c.op,
          value: c.value,
          params: c.params,
        })),
        limit: 100,
      });
      setResults(res.results);
      message.success(`Found ${res.total} stocks`);
    } catch {
      message.error("Screener failed");
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: "代码", dataIndex: "code", key: "code", width: 100 },
    { title: "名称", dataIndex: "name", key: "name", width: 120 },
    { title: "行业", dataIndex: "industry", key: "industry", width: 120 },
    {
      title: "信号",
      dataIndex: "_signal",
      key: "_signal",
      width: 150,
      render: (v: string) => v ? <Tag color="green">{v}</Tag> : null,
    },
    { title: "ROE", dataIndex: "_roe", key: "_roe", width: 80 },
    { title: "RSI", dataIndex: "_rsi", key: "_rsi", width: 80 },
  ];

  return (
    <PageContainer>
      <Card title="选股条件" style={{ marginBottom: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          {conditions.map((c) => (
            <Space key={c.key} align="center">
              <Select
                value={c.field}
                onChange={(v) => {
                  const defaultOp = OP_OPTIONS[v]?.[0]?.value || "gt";
                  updateCondition(c.key, { field: v, op: defaultOp });
                }}
                options={FIELD_OPTIONS}
                style={{ width: 150 }}
              />
              <Select
                value={c.op}
                onChange={(v) => updateCondition(c.key, { op: v })}
                options={OP_OPTIONS[c.field] || []}
                style={{ width: 80 }}
              />
              {!["ma_cross", "macd_cross"].includes(c.field) && (
                <InputNumber
                  value={c.value}
                  onChange={(v) => updateCondition(c.key, { value: v ?? undefined })}
                  style={{ width: 100 }}
                />
              )}
              <Button
                danger
                onClick={() => removeCondition(c.key)}
                disabled={conditions.length <= 1}
              >✕</Button>
            </Space>
          ))}
          <Space>
            <Button onClick={addCondition}>
              + 添加条件
            </Button>
            <Button
              type="primary"
              onClick={handleSearch}
              loading={loading}
            >
              🔍 开始筛选
            </Button>
          </Space>
        </Space>
      </Card>

      <Card title={`筛选结果 (${results.length})`}>
        <Table
          dataSource={results}
          columns={columns}
          rowKey="code"
          pagination={{ pageSize: 30 }}
          onRow={(record) => ({
            onClick: () => window.location.assign(`/stocks/${record.code}`),
            style: { cursor: "pointer" },
          })}
        />
      </Card>
    </PageContainer>
  );
}
